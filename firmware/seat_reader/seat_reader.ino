// Arduino UNO Q (MCU). Install MFRC522 + Arduino_RouterBridge.
#include <SPI.h>
#include <MFRC522.h>
#include <Arduino_RouterBridge.h>
constexpr byte SS_PIN=10, RST_PIN=9;
const char* READER_ID="reader-01"; // backend config maps this reader to B1_001.
MFRC522 rfid(SS_PIN,RST_PIN);
String session, pendingUid, pendingId;
unsigned long sequence=0,lastSeen=0,lastHeartbeat=0,lastRetry=0;
bool armed=true;
void setup(){
 Bridge.begin();Monitor.begin(115200);SPI.begin();rfid.PCD_Init();delay(100);
 byte v=rfid.PCD_ReadRegister(MFRC522::VersionReg);
 if(v==0||v==255){Monitor.println("RC522 not detected: check 3.3V, GND and SPI wiring.");while(true)delay(1000);}
 Monitor.println("Reader ready. Start Linux seat server, then tap one card.");
}
void loop(){
 unsigned long now=millis();
 if(session.length()==0){
  if(!Bridge.call("seat_session",String(READER_ID)).result(session)){delay(1000);return;}
 }
 if(now-lastHeartbeat>=5000){
  bool ok=false;Bridge.call("seat_heartbeat",String(READER_ID)).result(ok);lastHeartbeat=now;
 }
 // Retry the SAME event identifier until acknowledged: it cannot toggle twice.
 if(pendingId.length()&&now-lastRetry>=1000){
  String reply;
  if(Bridge.call("seat_tap",String(READER_ID),pendingUid,pendingId).result(reply)){
   Monitor.println(reply);pendingId="";pendingUid="";
  }
  lastRetry=now;
 }
 byte atqa[2];byte size=sizeof(atqa);
 auto status=rfid.PICC_WakeupA(atqa,&size);
 if(status==MFRC522::STATUS_TIMEOUT){
  if(now-lastSeen>=1000)armed=true;
  delay(80);return;
 }
 // Errors and collisions must not be mistaken for removal.
 lastSeen=now;
 if(status!=MFRC522::STATUS_OK){delay(80);return;}
 if(!rfid.PICC_ReadCardSerial()){delay(80);return;}
 if(armed&&pendingId.length()==0){
  String uid;
  for(byte i=0;i<rfid.uid.size;i++){if(rfid.uid.uidByte[i]<16)uid+="0";uid+=String(rfid.uid.uidByte[i],HEX);}
  uid.toUpperCase();pendingUid=uid;pendingId=session+":"+String(++sequence);armed=false;lastRetry=0;
 }
 rfid.PICC_HaltA();rfid.PCD_StopCrypto1();delay(80);
}

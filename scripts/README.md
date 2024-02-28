# Scripts

TODO implement some way to setup supervisory level logic that can interact with the server. Every building BAS has this these basic features:

* outside air temperature temp global value
  * BACnet read in boilers hard-wired outside temp
  * BACnet write to other devices requiring outside air temp
* alarm dial out
  * create logic that can find points that are in "alarm"
  * dial out to email service
* equipment schedule
  * find global occ schedule point on server
  * BACnet write to equipment that needs writing

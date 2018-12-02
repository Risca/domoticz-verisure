# Basic Python Plugin Example
#
# Author: GizMoCuz
#
"""
<plugin key="Verisure" name="Verisure" author="risca" version="1.0.0" externallink="https://www.google.com/">
    <description>
        <h2>Verisure</h2><br/>
        Allow control of Verisure devices. Uses the python-verisure library (https://github.com/persandstrom/python-verisure) for control.
        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>Turn on and off smart plug</li>
            <li>Read climate sensors</li>
        </ul>
        <h3>Configuration</h3>
        TBD
    </description>
    <params>
        <param field="Username" label="Username" width="200px" required="true"/>
        <param field="Password" label="Password" width="200px" required="true" password="true"/>
        <param field="Mode1" label="Polling interval (default 240 s)" width="200px" default="240"/>
    </params>
</plugin>
"""
import Domoticz
# Required for import: path is OS dependent
# Python framework in Domoticz do not include OS dependent path
#
import site
import sys
import os
path=''
path=site.getsitepackages()
for i in path:
    sys.path.append(i)
import verisure
from datetime import datetime

class BasePlugin:
    lastPoll = datetime.now()
    tick = 0
    next_unit = 1
    def __init__(self):
        return

    def onStart(self):
        if not Parameters['Mode1']:
            Parameters['Mode1'] = str(240)
        if Devices:
            next_unit = max(Devices.keys()) + 1
        return self._updateDevices()

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug('onCommand called for Unit ' + str(Unit) + ': Parameter '' + str(Command) + '', Level: ' + str(Level))
        try:
            turn_on = (Command == 'On')
            deviceLabel = Devices[Unit].Options['deviceLabel']
            with verisure.Session(Parameters['Username'], Parameters['Password']) as session:
                session.set_smartplug_state(deviceLabel, turn_on)
            Devices[Unit].Update(nValue=1 if turn_on else 0, sValue=str(Command))
        except verisure.Error as e:
            Domoticz.Error('Verisure exception: {}'.format(e))
            pass
        return True

    def onHeartbeat(self):
        lastPollDelta = (datetime.now()-self.lastPoll).total_seconds()
        pollingInterval = int(Parameters['Mode1'])
        if lastPollDelta > pollingInterval:
            self._updateDevices()
            self.lastPoll = datetime.now()

    def _getDomoticzDeviceList(self):
        return {dev.Options['deviceLabel']: unit for unit, dev in Devices.items()}

    def _updateDevices(self):
        Domoticz.Debug('Updating devices')
        try:
            with verisure.Session(Parameters['Username'], Parameters['Password']) as session:
                overview = session.get_overview()

        except verisure.Error as e:
            Domoticz.Error('Verisure exception: {}'.format(e))
            return False
            pass

        current_devices = self._getDomoticzDeviceList()
        
        remote_devices = set()
        for plug in overview['smartPlugs']:
            is_on = (plug['currentState'] == 'ON')
            device = plug['deviceLabel']
            remote_devices.add(device)
            if device not in current_devices:
                Domoticz.Log('Adding smart plug ({label}) in {area}'.format(label=plug['deviceLabel'], area=plug['area']))
                Domoticz.Device(Name='Smart plug', Unit=self.next_unit, TypeName='Switch', Options={'deviceLabel': device}).Create()
                current_devices[device] = self.next_unit
                self.next_unit = self.next_unit + 1
            unit = current_devices[device]
            Devices[unit].Update(nValue=1 if is_on else 0, sValue='On' if is_on else 'Off')

        for climate in overview['climateValues']:
            has_humidity = 'humidity' in climate
            device = climate['deviceLabel']
            remote_devices.add(device)
            if device not in current_devices:
                Domoticz.Log('Adding climate sensor ({label}) in {area}'.format(label=climate['deviceLabel'], area=climate['deviceArea']))
                if has_humidity:
                    Domoticz.Device(Name='Climate sensor', Unit=self.next_unit, TypeName='Temp+Hum', Options={'deviceLabel': device}).Create()
                else:
                    Domoticz.Device(Name='Climate sensor', Unit=self.next_unit, TypeName='Temperature', Options={'deviceLabel': device}).Create()

                current_devices[device] = self.next_unit
                self.next_unit = self.next_unit + 1

            unit = current_devices[device]
            temperature = climate['temperature']
            if has_humidity:
                humidity = int(climate['humidity'])
                Devices[unit].Update(nValue=0, sValue='{t:.1f} C;{h};1'.format(t=temperature, h=humidity))
            else:
                Devices[unit].Update(nValue=0, sValue='{t:.1f} C'.format(t=temperature))

#        for doorWindow in overview['doorWindow']['doorWindowDevice']:
#            device = doorWindow['deviceLabel']
#            remote_devices.add(device)
#            if device not in current_devices:
#                Domoticz.Log('Adding door/window sensor ({label}) in {area}'.format(label=doorWindow['deviceLabel'], area=doorWindow['area']))
#                Domoticz.Device(Name='Door/window sensor', Unit=self.next_unit, TypeName='Switch', Switchtype=2, Options={'deviceLabel': device}).Create()
#                current_devices[device] = self.next_unit
#                self.next_unit = self.next_unit + 1

        removed_devices = current_devices.keys() - remote_devices
        for device in removed_devices:
            unit = current_devices[device]
            Domoticz.Log('Removing device {unit} (\'{device}\')'.format(unit=unit, device=device))
            Devices[unit].Delete()
        Domoticz.Debug('Updating devices - done')
        return True

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()


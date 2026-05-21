# Automatisert robotsorteringssystem ved hjelp av datasyn og fargegjenkjenning
 Dette er ett prosjekt laget av:
 - Nooman Ahmed
 - Mandira Dhakal
 - Leander Tennebø
 - Sander Weme

Hovedfilen er main. Der vil man finne hele prosjektfilen med koden brukt for test forsøkene. Den inneholder også prototypen av digital shadow, som kun har grafikk og en simpel animasjon som kan bli brukt for å koble til hva som skjer i sanntid. Det er også en fork som heter DigitalShadow_Robot som har en utvidet robot objekt som er mer utviklet for å kobles opp senere for oppdragsgiver dersom de vidreutvikler dette, og velger å bruke python metoden.

## How to use:
- Step 1: Kjør \interface\app.py
- Step 2: Åpne http://10.212.66.45:5000/ i en nettleser
- Step 3: Koble roboter, og kamerar til datamaskinen
- Step 4: Identifiser portene hvilken robot har (fint å bruke dobot studio for dette)
- Step 5: i \Python_Project\get_port.py sett dobot 1 til "rail", og dobot 2 til "conveyor" med de comportene fra step 4.
- Step 6: Home robotene
- Step 7: Start med Async valgt

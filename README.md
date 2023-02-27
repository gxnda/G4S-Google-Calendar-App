# G4S_API_UI

Requirements:
- The user must log in with their Go4Schools Login, I haven't added options for Microsoft etc. yet.
- If the packages are not installed, pip must be installed and on %PATH%. If it isn't on path, you will have to do some tinkering to the install() function to get it to work.



Bugs:
- If invalid date selection, it will continue as if you left it blank (Current week).

- Cannot find if homework event already exists, it works but not 100% of the time and I have no idea why. I have added a "Remove Duplicate Events Button" to counter this but it sometimes just deletes double lessons and I have no idea why also. You have to go -> add homework events -> remove duplicates -> add timetable events

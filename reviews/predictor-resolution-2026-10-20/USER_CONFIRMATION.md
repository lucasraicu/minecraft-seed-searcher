# Independent player confirmation

After being given seed `-9103892851552028103` and teleport command
`/tp @s 820 16 -1708`, the user replied:

> omg you were right there is a stronghold here

This corroborates the BDS copied-world `getGeneratedStructures` result and saved
block evidence. The user's local game build and exact world settings were not
independently supplied; do not silently attach a version or portal-room claim.

Preserve the static stronghold enumeration. `/locate` returned another stronghold
at (98,-2030); that remains a navigation/query discrepancy, not physical absence.


## Village follow-up

After being given seed `-3509659830737203357`, coordinates X=-296,Z=-312,
Snowy Plains (`ice_plains`), surface aboutY77 and teleportY85, the user replied:

> no village here

This agrees with the BDS whole-start-chunk membership audit: zero village member
blocks throughout bounds[-304,-64,-320,-288,320,-304] (half-open). The positive
village start chunk contains11264village-member blocks. Together these support
classifying this specific predicted start as a false positive. They do not prove
an exhaustive27-village world census or establish an Ancient City exclusion rule.

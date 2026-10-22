# Internal Realm observations (public filter registry remains31)

Personal Realm scoring includes ocean_ruin, buried_treasure and basement-filtered
igloos; these are not all publicqueryfeatures. Store shared internalfacts once in
obs.realm.inventory, notperanchor. Do notchange public31feature/v1bytecontracts.

Implement realm_observations.py, no nativeimports/launch/storage. APIs:
extract_realm_inventory(obs, backend)->obs (maymutate; preserveotherrealmkeys).
validate_realm_inventory(obs)->inventory (raiseValueError; no backendcalls).
Backend: structures(name,inclusive_bounds,viable=True),igloo_basement(x,z)->bool,
bastion_variant(x,z)->int0..3. Publicstarts:obs.structures['structure.igloo'] and
['structure.bastion']; their coverage.status controls complete enumeration.

Inventory exact4keys ocean_ruin,buried_treasure,igloo_basement,bastion_variant.
Eachentry exactkeys status,bounds,method_id,points,errors. status oneof
unknown/partial/complete/failed; bounds dimension's obs.bounds (closed-open).
errors:list<=10strings<=500chars, no credentials. points sortedunique<=200000.
Oceanruin/buriedtreasure scan OW box once, deduplicate[x,z], method
predictor_viable_starts_v1. Backendfailure =>failed, missinginventoryneverzero.
Igloobasement querieseachknownigloo: true positives[x,z], method
predictor_igloo_basement_v1, completeonlyifsourceigloo coveragecomplete andall
queries succeeded. Unknown sourcecoverage/anyqueryfailure =>partial withknown
positivewitnesses retained. Bastionvariant similarly usesNetherstarts andpoints
[x,z,variant], methodpredictor_bastion_variant_v1, completeonlyifpublicbastion
coveragecomplete andallqueries succeeded. Failedvariant mustnotbeinventedzero.
Allcoords integer(notbool), inside relevantbox. Variantinteger0..3. Auxigloo/
bastioncoordinates mustbesubsets oftheirpublicsource starts. Completeentries
withunchangedbounds/method mayresume skip; otherentries resurvey. Validateall
existingrecords beforetrustingcompletion. Freshobs.realm=None becomesdict with
inventory; otherrealmkeys unchanged. No prototypeevaluation inthismodule.

Sourcebound replay/publication uses normalobservationhash; internalfacts remain
predictions, notphysicalbasement/treasureroom verification. Unitstubtests only:
queries/bounds/dedup/resume/errorstatus/unknowncoverage/subsetvalidation/variants/
strictinvalidcoord types. No terminaltools; coordinator runsdeclaredpytestcheck.

# V2 product UI integration

Registry GET /api/catalog/products returns catalog-products-v1 orv2 withproducts.
Pillar IDs realm,presets,personalized,rare. availability_status research is legacy,
predicted is v2launch product, gated staysunavailable. Product hasid,label,category,
criteria_summary,scope,ranking,missing_dependencies,evidence_needed.

POST /api/catalog/product-results:
{revision:'catalog-product-request-v2',snapshot_id:SHA64,product_id:string,
 page_size:20,cursor?:string}. Response:
{ok:true,revision:'catalog-product-results-v2',snapshot_id,product_id,
 results:[evaluation],matched_worlds:int,next_cursor:string|null,
 population_worlds:int,evaluation_counts?:{match:int,no_match:int,pending:int}|null,scope,policy_revision:SHA64,evidence_label:string}.
Error bodies use{ok:false,error,code}; oldsnapshots mayreturn product_gated409.

evaluation={product_id,world_id:SHA64,seed:signed64string,observation_id:SHA64,
 status:'match',rank:list,anchor:{mode,coordinate:[x,z],overworld:[x,z],
 nether:[x,z],nether_reference?},
 witnesses:[{feature,dimension,coordinate:[x,y|null,z],distance_squared:int,
 provider,observation_id,witness_id}],metric:object,reason:null,
 scope:{dimension,radius}}.
Metric keys:count/count_complete for density; farthest_witness_d2 forpreset;
score/qualifying_core/nether_core/components forRealm; cluster_center/radius_squared
forclusters;families/ranking forbiomesampler. Missingmetrics remainunknown.
Fractions mayuse{numerator,denominator},never assumeallranksarenumbers.

Realm has separate2048/4096/8192 boards, max1250 each; fixedgroups845OW/265luxury/140Nether.
Largerboards use frozen empirical count schedules in realm_calibration.json. Nether stays1024square. The legacy2048 metric calibration_pending is not the registry activation authority; each board has its own versioned evidence.
Presets16,launchrecords17. Five terrain-heavy proposals are removed from the
current registry; their historical IDs remain in the frozen contract and legacy
registry. Current UI must not advertise them as deferred future work.
All geometryhorizontal:OWradii150/200/300 etc;Netherblocksseparate, projectfloor(OW/8),
notverifiedportal. Scalarcountis distinctpredictedstartcoordinates,notphysicalcensus.
No walkable/farm/safe/footprint/height promises beyondsavedbiomeYwitnesses.

PreservelegacyResearchList. Addv2listrealresponses withpagination20, copyseedtext,
anchor/dimension/witnesses/criteria andpopulation-scopedrank, loading/empty/error.
Abortandepochguards mustrejectwrongPID/SID/staleresponses. Eachrequestmustsend
selectedsnapshotID. UserwaivedinteractivebrowserQA;actualReactrenderchecksrequired.

P1capacity isversioned3334/3333/3333 across2048/4096/8192, total10000. Larger policies activated after independent selected-control/oracle validation; see realm_calibration.json for the frozen scope and zero original holdout matches. No population-rate claim.

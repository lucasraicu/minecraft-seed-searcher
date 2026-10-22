# Bounded pure calibration fitter

Implement catalog/calibration.py only (no native/server/jobs). Data input:
rows=[{world_id:SHA64,split:'development'|'held_out',counts:{'2048':{feature:int},'4096':{feature:int},'8192':{feature:int}}}].
Base schedules mapfeature->{floor:int,levels:[strictlyincreasingintegercounts,
first==floor]}. Levels list includes floor0 foroptionalfeatures. NeverfitNether:
caller passes OWfeatures only. Budgets/pointincrements are outside thismodule.

fit(rows,schedules) -> {revision:'catalog-size-thresholds-v1',sizes:{'2048':{feature:
{base_levels:list,thresholds:list}},'4096':..., '8192':...},diagnostics:...}.
Use ONLYdevelopment rows to select thresholds; fail if anyfeature/sizemissing or
invalid counts, duplicateworld IDs, unknownsplits, nonfinite/booleanvalues,
no developmentrows, malformed schedules. Count bound200000. World splitpreserved.

Preserve2048 thresholds EXACTLY. Optionalfloor0 stays0; hardpresencefloor1 stays1
atall sizes (basic availability, avoids arbitrary loss of goodworlds). Floors>1
and countbonus tiers adapt. For eachbaseline tierT:
- Compute empiricaldevelopment tailprobability P(count2048>=T).
- Fit larger k>=baselineT, >=samefeature previoussize level, and strictlygreater
than preceding level atthissize. Minimize ABS difference in empirical tail
probability (use exact fractions forcomparison); integer ties chooseclosest to
an affine reference: meanS+(T-mean2048)*stdS/std2048. Ifbaseline variance0 use
mean shift and flagit asdiagnostic; noPoisson/area assumption.
- When BOTH baseline andlarger hit the ORIGINAL tier fewerthan5times, preserve
that sparse tier unless monotonicity forcesit up. This is an explicitlyfrozen
modeling policy, not a universalstatistical guarantee. Record sparse-tier flags.
- Include allintegers from lowerbound through maxobservedlarger+1 (or derive
CDFplateau equivalents without a largecomplexity increase). Boundstiercount<=32,
features<=32,cohort<=2000,counts<=200000; avoidquadratic percount loops.
Thresholds selectedfromdevelopment data arefrozen beforeheldout metrics.

map_count(count,entry)->baselineequivalentintegercount fordynamic_v3_score:
belowthresholdfloor returnmax(0,basefloor-1), otherwise highestbaselevel whose
threshold was reached. Exact2048 values abovehighestlevel mayclamp tolasttier
(the pointformula isalreadycapped); no pointformula copies inthismodule.
Monotone countmapping; fixedbudgets preservedbyexisting scorer.

diagnostics report measureddevelopment/heldout tailhits/n perfeature/size/tier,
fitmethod/sparse/zerovariance flags. Heldoutcounts MUST NOTaffect fittedthresholds.
Do notinvent confidenceintervals/acceptancerates/guarantees or silentlyactivate
boards. Caller ownsactivationreview,sourceidentity,artifactstorage andUI.
Tests needhand-computable CDF/tie cases, zero variance, missinginputs, original
2048unchanged, heldoutpoisoning, count/size monotonicity andcapmapping.

# Cubiomes-viewer User Guide

Version 1.0  
Written by Jereaux  
with contributions from mooing\_cowmilk, NelS, daneeko, Stofix, and Cubitect  
Cubiomes-viewer created by Cubitect

Contents  
[Introduction	3](#introduction)

[Minecraft Seeds	4](#minecraft-seeds-\(seedfinding,-not-seedcracking\))

[Chapter 1: Cubiomes-viewer Interface	5](#chapter-1:-cubiomes-viewer-interface)

[Chapter 2: Search Conditions Introduction	10](#chapter-2:-search-conditions-introduction)

[Chapter 3: Biome Condition Type	14](#chapter-3:-biome-condition-type)

[Chapter 4: Structure Conditions	20](#chapter-4:-structure-conditions)

[Chapter 5: Algorithm Helpers	21](#chapter-5:-algorithm-helpers)

[Chapter 6: Others Conditions	23](#chapter-6:-others-conditions)

[Chapter 7: Nether & End Biome Conditions	24](#chapter-7:-nether-&-end-biome-conditions)

[Chapter 8: Quad Structure Conditions	24](#chapter-8:-quad-structure-conditions)

[Chapter 9: Basic Searches	25](#chapter-9:-basic-searches)

[Chapter 10: Optimizing Search Conditions	28](#chapter-10:-optimizing-search-conditions)

[Chapter 11: Seed Analysis	30](#chapter-11:-seed-analysis)

[Chapter 12: Session Files	32](#chapter-12:-session-files)

[Chapter 13: Settings	33](#chapter-13:-settings)

[Chapter 14: Putting It All Together	39](#chapter-14:-putting-it-all-together)

[Appendix	42](#appendix)

## Introduction {#introduction}

Cubiomes Viewer is a seedfinding program for the various versions of Minecraft Java Edition, capable of finding seeds satisfying particular conditions involving biomes, structures, the world spawn, and so on. It is effectively a Graphical User Interface (GUI)-based implementation of the Cubiomes library, both of which were created and are maintained by Cubitect. This guide was created for Version 3.2.1 and focuses on the specific features of Minecraft Java versions 1.18+, though much of the information here will work across all versions. As of Bedrock version 1.18.20.21, Bedrock and Java editions share biome parity, so this tool can also be used for biome specific searches for Bedrock edition after that version. 

## Minecraft Seeds (Seedfinding, not seedcracking) {#minecraft-seeds-(seedfinding,-not-seedcracking)}

There are over 18 quintillion seeds in Minecraft with all seed numbers between ± 9,223,372,036,854,775,807. On top of that, each Java seed is 60 square million blocks (3.6 quadrillion surface blocks). The scale of just how much area this encompasses with how many possibilities there are, is almost unfathomable. 

People often envision they will be able to find their old seed using a tool like Cubiomes Viewer, but that is for all intents and purposes impossible. When “seedcracking” is performed, it usually is done by reversing tree or dungeon generations–to (put simply) obtain a set of intermediate seeds that could have generated said tree or dungeon, and then continuing from there. Cubiomes Viewer, however, is completely unable to perform such “backwards” reasoning; it can only search “forwards” by iterating over each seed and seeing whether the necessary requirements hold, which while certainly a more generally applicable approach, also makes finding any “unique” seed all but impossible. 

As an analogy, imagine on a trip to the Sahara Desert you pick up a grain of sand. It has a unique shape to it, and you decide you really like this grain of sand. It feels different from all the other sand you see. By chance though, you accidentally let go of the grain of sand, and it’s picked up by a gust of wind and blown away into some unknown part of the desert. 

Then you decide you want to find that grain of sand again, so you try to remember all the details you can about the grain of sand. Maybe it had a black spec on one side, was mostly round but had a jagged piece on one side, and it was slightly smaller than the other sand. 

Suppose there exists a tool that you can input what you remember about your favorite grain of sand, and it can find matching pieces of sand from that. Once you enter what you remember, the tool can pick up a cubic centimeter of sand a second, scan all the pieces of sand, and tell you which grains of sand match what you remember. 

Now that you have set up the tool, you just need to run the tool across the whole Sahara Desert. 

Because you can’t remember super specific details of the grains of sand, you pick up about 2 trillion grains of sand that match the details you remember, and you will now need to hand check each one of those 2 trillion grains of sand to see which one was the specific grain you had. 

Cubiomes-viewer is that tool. And that grain of sand is the seed you remember. 

## Chapter 1: Cubiomes-viewer Interface {#chapter-1:-cubiomes-viewer-interface}

There are five main sections of the Cubiomes-viewer interface which provide fields to input version and seeds to view, set up conditions, and select from lists of seeds matching your searches. It also includes a map to display the elements of a selected seed including biomes, structure, terrain, and noise. 

### Versions, Seeds, and Y-Layers

* Cubiomes viewer supports 20 versions of Minecraft, and generally displays and supports the features of the last sub-version of each major version. Prior to a new version coming out it may also include experimental features from snapshots that may contain bugs.  
* It can also support searching against the Java Large Biomes seed category, and checking the box will immediately change the map display to the Large Biomes features.   
* Seeds can be entered in the seed field to change the map display to the features of that seed. This can be a string of numbers, or characters which will automatically convert the characters to the seed number associated with those characters. You can click on a seed in the Matching seed list to have it pulled into the field.  
* The Y level displayed on the map can be changed to view biomes at different layers. This will overlay the surface biomes if cave biomes exist below the surface. Cave biomes cannot exist at Y: 256

### Conditions

* The search conditions define the properties by which potential seeds are filtered.  
* Each condition is assigned a number when first created, and that number can be used as a reference for that specific condition in order conditions, however that number does not dictate the order in which conditions run.   
* Conditions are processed in the order they appear on the condition list. Conditions that reference other conditions must appear lower in the list as that condition will be dependent on the first condition.   
* There are many different condition types that can be filtered against. These include Biome, Climate (Perlin noise wave values), Structures, Spawn, Terrain Height, Slime Chunks, and dimensional variations including overworld, nether, and the End.  
* Conditions can be disabled or enabled for testing or for using one session to process more than one search type. Select one or more enabled conditions and click the “Disable” button to exclude the conditions from the next started search. To enable conditions, click on one or more disabled conditions and select “Enable”. If multiple condition status types are selected, the button changes to “Toggle” that will change the status from Enabled to Disabled, and from Disabled to Enabled.  
* Creating your conditions to filter against is key to being able to find the type of seed you want. There are many ways to create a condition set to find a seed you are looking for, so experimenting with different methods may help you find the fastest method of searching, though be careful of creating impossible conditions or condition sets. See “[Optimizing Search Conditions](#impossible-conditions)” below for hints on how to create faster searches. 

### Seed generator

This provides additional tools for 48-bit seed searches, finding suitable options based on the conditions you input that would fall into a search type that this can utilize. As I do not have familiarity with this specific process, the below quoted information is found directly in cubiomes-viewer. Future updates to the guide may include additional information. 

“For some searches, the 48-bit structure seed candidates can be generated without searching, which can vastly reduce the search space that has to be checked. 

The generator mode Auto is recommended for general use, which automatically selects suitable options based on the conditions list. 

The Quad-feature mode produces candidates for quad-structures that have a uniform distribution of region-size=32 and chunk-gap=8, such as swamp huts. 

A perfect Quad-monument structure constellation does not actually exist, but some extremely rare structure seed bases get close, with over 90% of the area within 128 blocks. The generator uses a precomputed list of these seed bases. 

Using a Seed list, you can provide a custom set of 48-bit candidates. Optionally, a salt value can be added, and the seeds can be region transposed.”

### Matching Seeds and search options/display. 

* The Matching Seed list is populated as the search engine finds seeds that match the conditions specified in the “Conditions” list. Additionally, seeds or seed lists can be pasted into the Matching Seed list for ease of viewing or running additional analysis against.   
* The Seed list by default orders the seeds in order of them being found or pasted in. If you click on one of the headers, the list will re-sort in either ascending or descending by the column selected.   
* The first column lists the seeds found. The 2nd column is the top 16 bits of the seed found. The third column lists the lower 48 bits of the seed. Seeds with the same 48-bit values will share some similar characteristics such as having the same nether, or sharing where structures will potentially spawn when biome and other required conditions are met.   
* To run a search, you will need to click the “Start search” button, however there are some search options you may want to set prior to starting your search.   
* Search Type: There are three different search types, Incremental, 48-Bit family blocks or Seed list from a file.  
  * An incremental search type starts the search at the Minimum seed selected (default 0\) and increments up through the entire seed list of over 18 quintillion seeds.   
  * The search range shows positive seed numbers starting at 0, however the first half of the numbers are the positive seed number set, and starting at approx. 9.22 quintillion, the negative seed set will be searched against. For example, to start your search at \-8.44 quintillion, enter 10 quintillion into the Minimum value and the search will increment up towards 0\. The \[…\] button next to the Search selection drop down will show you where the search will start and end. Restore Defaults will set the min to 0 and the max to 18.4467… quintillion.   
  * 48-bit family blocks can search through the full seed list of all seeds, but first searches against the 48-bit candidates inside the master search thread. Once a match is found, the related 48-bit seeds (65536 seeds) are checked among the worker search threads. This search type is most useful for finding seeds with similar structure placements and can be significantly more efficient at covering the search space since ruling out any given 48-bit seed will skip a whole family of related seeds.  
    * Sister seeds area seeds in Java v1.17 and earlier with the same lower 48-bit, and they share many similarities including the same Nether Generation, End Generation, Caves and Ores, Possible Structure Locations, and other features when certain conditions are met (Terrain, Creature Spawns, Chest Loot).   
  * Seed list from a file… processes a search against a file that you have outside Cubiomes-viewer and must load in for the search to occur.   
    * This can be useful when processing searches against difficult sets of criteria. If you want a lot of conditions to be met, you can narrow your search criteria to be faster but generate lots of results, and then run further searches against the first list generated for the more challenging criteria that might have otherwise slowed your original search.   
* Threads allows you to select the number of CPU threads Cubiomes-viewer will use to process your search. You can pick from 1 up to the number of threads your CPU allows. The search will be faster, but also use much more CPU power and require more cooling to run. Also note that different types of CPUs will run at different speeds even for the same number of threads, so your seeds/second may be different from someone else even when all factors of your search are the same.   
  * Additionally, your own CPU may have different thread speeds for different cores. For example, many new Intel CPUs have Power Core, Efficiency Cores, and Dual threads on the power cores. Each one of these will run at different speeds, so doubling your threads may not result in double the speed of the search. v1.18+ Biome searches are unable to utilize Hyperthreading effectively, providing little or almost no gains in efficiency on many CPUs.

### Map, dimension, and structure display {#map,-dimension,-and-structure-display}

The map is a graphical representation of the Minecraft world generated by the seed in your seed field. Each color represents a different biome, and structures can be toggled on and off in the map using the icons on the right. 

The map defaults to show the overworld, but the nether and end dimension can also be displayed. The map display can be changed in many ways using the top menu to toggle different features. For example, you can change the color of the specific biomes, change to a topographical view of the map, or change the grid spacing. 

Right clicking on the map provides additional options for copying the seed numbers, coordinates (block, chunk or region), or a teleport command you can paste into Minecraft to teleport to the block where you right clicked (does not set the Y value). 

You can also select “Go to coordinate” to center the map to a new location. If you don’t change the scale value, it will stay zoomed to the same level you had on the map. You can change it to a new value to zoom in or out. You can also check to animate the change in centered location for a smooth transition to the new location.


## Chapter 2: Search Conditions Introduction {#chapter-2:-search-conditions-introduction}

There are a number of different Condition and Category Types that can be selected to create differing searches. Some condition types are used for filtering different biome and structure locations. Others are tools to help add additional logic to other conditions. 

### Algorithm helpers: 

* Logic Gates  
  * The OR and NOT logic gate allow you to add additional logic to your search. Add your Logic Gate above the condition you wish to apply the logic to, then reference one or more conditions against the logic gate. The OR will require one of the conditions referenced to be met. The NOT means that the condition must not be met (for Biome exclusions this will only ensure that the exclusion passes at one point rather than the whole area)  
  * See [Chapter 5: Algorithm Helpers](#chapter-5:-algorithm-helpers) for additional information on how to setup Logic Gates  
* Coordinate Factors  
  * Coordinate factors allow you to add search conditions that can reference between the Overworld and Nether which use different factors of distance.   
* Lua (Coding)  
  * This is a new condition type that allows you to write your own LUA coding against the Cubiomes library for generating queries.   
* Spiral Iterators (formerly Reference Points)  
  * The default search value for any seed is “World Origin” which is at 0,0. Spiral Iterators allow you to add additional starting points for your conditions. The ratio you pick (1:1, 1:4, 1:16 … 1:1024) are how far apart the search points are for your reference.   
  * When using a Spiral Iterator, the condition that references the iterator will pass if any single point in the iteration is true for that condition. This means it can’t be used as a biome exclusion for a wider area than the size of the biome condition. 

### Quad-structure

Quad structure is a special type of search that Cubitect added to the program to look for sets of 4 structures (Witch Huts and Ocean Monuments) that are close enough to allow for a mob farm. 

### Structures

* Structure searches allow you to search for any type of overworld, nether, or end structure in a defined area. You can search for 1 or a defined number of structures within that defined area, though be aware if you set too many structure searches for a small area it may not be possible to meet that condition.   
* You are also able to set exclusions for areas to ensure the structure you defined does not appear in a certain area.   
* Village structure types allow you to set additional conditions to search for specific variants based on the starting piece, or whether it’s abandoned. This will allow you to find specific variants such as Plains Fountain villages or the specific biome meeting point starting pieces. 

### Biomes

There are three primary types of Biome specific search types.

* Biome searches allow you to search for biomes in the Overworld to see if they show up (at least once) in a defined area, or to set up exclusions for biomes in a defined area. The defined ratio determines how much of that area is checked. 1:16 refers to checking every 16 blocks in the defined area.   
* Climate Parameters allow you to search against certain Perlin noise values that make up the basis for determining biomes or the layout of terrain in a defined area.   
* Locate biome center allows you to search for a specific minimum size of biome in an area. You pick a defined area, then input the minimum block area of a single biome type you want to show up in that area.

### Nether biomes

Like the Biome search category, this type allows you to search against Nether biome types using a defined ratio that determines how much of a defined area is checked. 1:4 refers to checking every 4 blocks in the defined area. 

### End biomes

Like the Biome search category, this type allows you to search against End biome types using a defined ratio that determines how much of a defined area is checked. 1:4 refers to checking every 4 blocks in the defined area. 

### Others

There are 4 “Others” search type conditions you can set up to search against. 

* Spawn – Allows you to search for the spawn point. This is a Very Slow condition type search.   
* Slime Chunk – This allows you to search for slime chunks in a given area.   
* Surface Height – This allows you to check a single point for an approximate terrain height for the overworld. This does have some limitations regarding certain biome types (especially windswept) and can be a very slow condition type search.   
* First Stronghold – This is an alternative structure search for the initial stronghold that generates in the world. This search condition is more of an approximation than the Structure Stronghold but runs considerably faster than looking for any Stronghold in a given area. 

### Condition Editor General Values

Once you have selected your Condition Type and Category, General fields show up on all condition categories.  

* Label: allows you to rename the default Biome 1: N label that displays on the “Condition” list in the main Interface. This can be used to help track the different conditions that are set up for your search.   
* Condition Enabled (Check Box) this allows you to enable or disable the condition when running a Search. This can also be edited from the Enable/Disable button on the Condition interface on the main window. 

### Condition Editor Location Values

* Instances within area  
  * Available for structure, slime chunk, or locate biome center search types, this field allows you to set the condition to exclude a structure type in an area (by selecting 0), or to search for 1 or more structures of that type in the defined search area.   
* Within radial distance  
  * This field accepts numeric input for most structures or spawn that defines the radial distance that your search condition must fall in. This will create a circular search area rather than search against a square area.   
* Within centered square of side  
  * This field accepts a numeric input that defines a square search range to find matching instances to the biome conditions you set in the Condition Editor. The number input will be multiplied by the ratio you selected. For structure or other conditions with no ratio, then the number will be the length of the center point of the search to the edge.   
* Custom  
  * Custom allows you to set a custom range to search against. The X and Z fields can accept a range of numbers that will create a grid of blocks to check every N number of blocks for condition types with ratios depending on the ratio you selected. So X1 \= 2 will multiply 2\*N and will start the initial X value at that point. For condition types without ratios, it uses the blocks you input for the full search area.   
* Location is relative to  
  * Use this field to reference another condition. This will allow you to search for biomes in relation to another met condition, such as a structure or a specified other search point. 

### Search Algorithm

The search algorithm generally performs two main search passes. The first one checks a seed without using a biome generator, while the second search pass tests everything, including biomes.

When a condition is evaluated, it yields a status that indicates whether the condition is satisfied, violated, or undecided in the current search pass. Additionally, it may yield one or more positions, so that referencing conditions know where they are positioned. The position is always valid if the condition is satisfied, and potentially valid if the condition is undecided.

Take this example filter with two conditions:

\[1\] Village             	x2  	r\<300

\[2\] Slime chunk         	x4  \[1\]+(-16,-16),(15,15)

In the first search pass, a seed is checked for two village generation attempts within 300 blocks and all seeds that fail to meet this, are discarded. Since we are testing for a structure cluster, the village positions are averaged for the referencing condition. Here it cannot yield a valid position yet, since it doesn't know which of the four potential villages in that area will actually generate, so the search will not propagate to the slime chunk condition.

On the second search pass, the villages are checked again, including biomes, and the condition yields the average of all the villages in the area (which can be more than the required two). That average position is then used to check the slime chunks.

Something else happens if we only check for a single village:

\[1\] Village             	x1  	r\<300

\[2\] Slime chunk         	x4  \[1\]+(-16,-16),(15,15)

Now the village condition can yield multiple instances that are checked separately.

On the first search pass, without the biome generator, we can find up to four village attempts that all have known positions. In this case, each village within range can already yield its position for the slime chunk condition. Seeds that don't have a potential village with four slime chunks are discarded.

The second search pass performs the same tests again, but this time includes the biome checks for the villages.

As it happens, a lot of conditions that can be checked without biomes only need the lower 48-bit of the seed. The search mode, 48-bit family blocks, uses this to look for 48-bit seeds using the first search pass. Only the matching seeds are then split into the 65536 associated 64-bit seeds and are checked as normal. This can be a significantly faster way of covering the search space, since it can potentially skip 65535 calls to the first search pass that would otherwise happen in the incremental search.

## Chapter 3: Biome Condition Type {#chapter-3:-biome-condition-type}

Biome search condition types are broken down into different categories, each with a ratio beside the condition type (except for Temperature categories). This guide will focus on the biome searches available specifically for version 1.18+ 

### Biome Ratios (1: N)

| Biome 1:4 | Biome 1:16 | Biome 1:64 | Biome 1:256 |
| :---- | :---- | :---- | :---- |

The ratio that is listed beside each type of biome check defines how often the check occurs against the area selected. If you choose the 1:4 ratio, then the search for that biome type will occur every 4 blocks in the area defined. If you choose 1:64, the engine will look for that biome type every 64 blocks. This can result in either a very dense search, or a light search depending on the area size you define. 

If you think of searching an area ±16 blocks, choosing a 1:16 search will search 9 \[X, Z\] points:

| \[-16,-16\]  | \[-16,0\] | \[-16,16\] |
| :---- | :---- | :---- |
| \[0,-16\] | \[0,0\] | \[0,16\] |
| \[16,-16\] | \[16,0\] | \[16,16\] |

If you search the same ±16 area using a 1:4 search, it will search 81 points. 

| \[-16,-16\] | \[-16,-12\] | \[-16,-8\] | \[-16,-4\] | \[-16,0\] | \[-16,4\] | \[-16,8\] | \[-16,12\] | \[-16,16\] |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| \[-12,-16\] | \[-12,-12\] | … |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |
|  |  |  |  | \[0,0\] |  |  |  |  |
|  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  | … | \[12,12\] | \[12,16\] |
| \[16,-16\] | \[16,-12\] | \[16,-8\] | \[16,-4\] | \[16,0\] | \[16,4\] | \[16,8\] | \[16,12\] | \[16,16\] |

Each ratio has its uses for different types of searches and picking the correct one will depend on the size of biome you’re looking for, or a biome that is a relative position to another condition (E.G., wanting to find a specific biome type directly over a stronghold). It’s important to try and pick the ratio that will best suit your needs for a specific search. Finding a big ocean with the potential for small islands is a great use for a 1:256 (land biomes slipping between the ocean check every 256 blocks), while you may not want to use that if you are looking for a lot of specific biomes near 0,0. In that case a Biome 1:16 search might be better suited. A bigger ratio search for the same size area will result in higher search speed, but with a tradeoff for search precision. 

The “Biome” search types will perform a search for the specific biome(s) selected or excluded by the user. If the biome is selected, the search will occur against the area defined by the user and look for any instance of that biome, passing the condition at the first instance found. If the biome is excluded, a search is performed against the whole defined search area and the check passes if none of the points searched contain that biome. The check will fail the first instance an excluded biome is found in that area. You can exclude all but a few biomes in an area to ensure that the 1:N check for an area only contains the biomes you are looking for.

### Creating a Biome 1: N Condition

* Match Any \- Check this box if you want the condition to be successful if Any of the selected (or only one excluded) biomes are found rather than all of them.   
* Biome: There are two types of biomes that can be searched in the overworld. Those that exist on the surface, and cave biomes that can only generate underground. The cave biomes are Lush, Dripstone, and Deep Dark.  If you try to search for a cave biome at surface height, you will receive a warning prompt to let you know that biome cannot exist at that Y height.   
* Sample at height (Y) \- At Y 256, only surface biomes can be searched. Cave biomes do not generate at that height. At lower Y values, you will either find a cave biome or the surface biome in a search if there are no cave biomes at that specific Y value.   
* Uncheck All \- This will clear any selection of Included or Excluded biomes.  
* Include All \- This will select all biomes to be “Included” in the search. If searching for all biomes, remember that cave biomes cannot be at Y256 Surface  
* Exclude All \- This will select all biomes to be “excluded” in the search. 

### Climate Parameters Explained

Climate Parameters are the Perlin Noise values that in combination are used to generate the various biomes and the layout of the land within Minecraft. While Minecraft uses more parameters than Cubiomes-viewer has for searching against, you can use the parameters to find specific biomes or mountains, valleys, and other terrain shapes. Here’s a quick explanation of each of the parameter types. 

*Temperature***:** a parameter used to determine which biome generates, and generally has a slow curve value from high to low temperatures. This means that biomes that generate in conditions for High Temperature values cannot be near biomes that generate in Low Temperature values. Some biome types can exist against a wide range of temperatures, though many fall into specific categories. 

Here is an approximate breakdown for temperature categories in Minecraft

* Temp \> 5500 – Hot Biomes (Badlands, Desert, Warm Ocean etc…)  
* Temp 5500 \> 2000 Warm Biomes (Jungle, Savanna, Lukewarm Ocean etc…)  
* Temp 2000 \> \-1500 Temperate Biomes (Birch Forest, Dark Forest, Ocean etc…)  
* Temp \-1500 \> \-4500 Cold Biomes (Taiga, Old Growth Spruce, Cold Ocean etc…)  
* Temp \< \-4500 Frozen Biomes (Snowy Plains, Snowy Taiga, Frozen Ocean etc…)

*Humidity***:** another parameter used to determine which biome generates. High humidity corresponds with more wet biome types (Jungle, Old Growth Spruce/Pine, Taiga, Wooded Badlands, Lush Caves), while low humidity corresponds to more dry biome types (Badlands, Ice Spikes, Meadow, Flower Forest, Savanna). Though some biomes such as desert, river, and all peaks can exist across the whole humidity range.

*Continentalness***:** determines whether land or ocean specific biome generates. Generally, there are 4 primary categories, though many biomes cross both land categories. 

* Continentalness \<= \-10500: Always Mushroom Island  
* \-10500 \< Continentalness \<= \-4550: Deep Ocean biomes  
* \-4550 \< Continentalness \<=  \-1900 Ocean Biomes  
* \-1900 \< Continentalness \<=  \-1100: Shore Biomes (Beach, Stoney Shore. Any biome which can border ocean)  
* Continentalness \< \-1100: Inland biomes. (Mangrove Swamp, Meadow, Cherry Grove, Savanna Plateau)

*Erosion***:** represents the flatness or inclines of land that generate peaks and plays a role in depth values and terrain height. A low erosion value tends to have large peaks nearby, while a high erosion value tends to have large flat swamps. 

*Weirdness***:** one of the primary elements of the peaks and valley noise value and is used in determining the terrain height of the land, though it does not impact the terrain of ocean. When centered over land, high and low weirdness produces biome lakes, with flatness around 0.6 and \-0.6 and steep terrain up around 0 weirdness. 

### Locate Climate Extreme 1:4

Like the Biome 1:4 search, Locate Climate Extreme’s base search is to look every 4 blocks in the area you define to be searched. Instead of looking for one or more biomes, the Locate Climate Extreme condition looks for a single Climate Parameter above or below the value you define. 

Locate Climate minimum/maximum

* Climate Parameter: \- Select the single climate parameter you want to search against.   
  * Temperature  
  * Humidity  
  * Continentalness  
  * Erosion  
  * Weirdness  
* Octaves: The octave option allows you to abort the parameter generation early to get a faster approximation and can be used to significantly speed up your climate parameter searches when used properly. Each climate parameter has its own set of octaves. Temperature and humidity only have 4, but continentalness for instance has more. These are ordered by increasing frequency and decreasing contribution to the final value.   
  * The octave code is constructed from several parts:  
  * A/B \- first/second octave of each double Perlin noise  
  * \[X\] \- the double Perlin noise index  
  * 1:X \- frequency scale (approximate)  
  * x0... \- value contribution of this octave  
* Locate value: This is how you define the value you want to search against, and then define whether to search to or from ±Infinity for that climate parameter. If you want to search from \-INF to \-4500, select Minimum \<= \-4500. If you want all values from 4500 to INF, then select Maximum \>= 4500\. If you want to make sure all the values in an area are above 5500, then pick Minimum \>=5500. If you want to make sure all values in an are below \-5500, select Maximum \<= \-5500. 

### Climate Parameters 1:4

The climate parameters condition type searches every 4 blocks for a range of climate parameters defined by selecting either Required or Confined values for one or more of the Climates listed. 

Required: The required value allows you to search to see if the climate parameter entered into the range selected in the area you defined. If you define a Required Temperature range from \-1000 to 1000, then the condition will look in the area you defined for any Temperature value in that range. If at least 1 block searched is within \-1000 to 1000 Temperature, the condition will pass. 

Full Range Check Box: To the left of the Required Climate range, there is a check box that allows you to define your search to find both the minimum and maximum value you selected in the area you defined. If you select a 200-block wide area, the condition will search for Temperature \-1000 AND 1000 in that area and will only pass if both values exist (checking for the full range of that Climate parameter in the area)

Confined: The confined search allows you to select a range for a Climate parameter that the whole area must meet for the condition to pass. If you select a Temperature range from \-2000 to 2000 in a 500-block wide area, all points that are checked within that area must have a Temperature between \-2000 and 2000\. If any Temperate value falls outside that range (-2001), then the condition will fail. 

Resulting biomes: The biomes aren’t selectable in Climate Parameters; however, each biome has a climate value range that it can show up in, and you can see those values if you hover your mouse over the biome name. 

If you select a confined range where that biome cannot exist, the \+ beside the condition will change to a – to indicate that biome cannot exist in the area you are searching based on the range selected. If you select a required range that the biome is not in, the \+ will change to a blank box. This indicates that you are searching for a range the biome does not exist in, but since the Required search allows for values outside the climate parameter range selected, that biome could still exist in the search area.


### Locate Biome Center 1:4

This condition allows you to select a single Biome, and to input a minimum size for the biome within a defined area. When inputting the minimum size in blocks, a quick calculation will be done by Cubiomes-viewer to ensure that the min size you input is not larger than the area you are searching for. This is to ensure you are not setting up an impossible condition such as searching for a 10 square chunks in an 8 square chunk area. 

Border tolerance is used to allow for small, disconnected patches of biome to be included in the biome sizing. The value you set will allow for these small patches to be included when the gap between the patches is less than the tolerance value.

## Chapter 4: Structure Conditions {#chapter-4:-structure-conditions}

A Structure condition can include a search for overworld, nether, or end structures. Certain types of structures have additional search criteria that can be included to look for a specific variant of that structure. This includes villages, nether fortresses, bastion remnants, ruined portals, and end cities. 

A structure search will default to look for one structure of the selected type in the area you define, however you can choose to search for more of that same structure type by increasing the Instances within area value. If you reduce the number to 0, the search will turn to an exclusion search, meaning that condition will pass if the structure does not generate in the defined area. 

Unlike a Biome search, you can search within a radial distance rather than a square or rectangular block area. Strongholds must spawn outside a radial distance of 1280 blocks in Java. 

Structures can also have limitations to where they can spawn that may be obvious, or hard to determine. Some are biome specific, such as desert temples only spawning in Desert, or the village type determined by the biome it spawns in. Other more hidden elements include specific parts of regions that structures cannot spawn in, such as only one village spawning per region, and villages not spawning in the southern or eastern 144 blocks (8 Chunks) of a 544x544 block area (34 Chunks). In Java, villages and Pillager Outposts are mutually exclusive to the same region, so if a Pillager Outpost or Village spawns in a region, then the other type of structure cannot spawn in that same region. 

Below you can find some examples of block areas where structures can and cannot generate closest to world origin. These block limitations continue to repeat further out from 0,0 and may be different in earlier versions of Minecraft (village generation area changed in 1.17 for example). 

Also see [Appendix B1 and B2](#appendix-b) for a sample map of where villages and mansions can spawn or are excluded from spawning. 

## Chapter 5: Algorithm Helpers {#chapter-5:-algorithm-helpers}

Algorithm helpers are not individual conditions that can be used to search for seeds, but other conditions can reference these conditions and provide some additional logic for search options. 

### OR Logic Gate

The OR logic gate allows you to search for instances where two or more conditions can pass if only one of the conditions passes. To set this up, the logic gate will need to come before the condition in the condition list and the condition(s) for the logic gate will reference the gate.

For example, if you wanted to search for Either a Desert Pyramid or a Jungle Temple in the first 100 blocks from World Origin, you could set up an OR logic gate that is referenced by those two conditions. If either a Desert Pyramid or a Jungle Pyramid is found within 100 square blocks of world origin, the resulting seed will be returned to the Matching Seed List. 

### NOT Logic Gate

The NOT logic gate allows you to search for instances where the condition you set will NOT be met. This is set up in the same way as an OR Logic Gate, but you only need one condition to be referenced for a valid search. You can reference more if you like but they will each run as their own separate check. 

The below NOT condition will pass when a Spawn location is outside of a 500 block radius from world origin. 

### Lua

Lua is a programming language and is generally considered one of the easier programming languages to learn. The Lua condition allows for writing Lua code to run against the Cubiomes library for more complex queries. At this time, I do not know how to best utilize this, but will add to the guide as I learn more about Lua coding. 

### Coordinate Factors X/8, X\*8

The coordinate factor conditions are used for being able to find block positions from the Overworld relative to the Nether. These conditions will both reference another condition and be referenced by another condition. For an example, go to the “Help” Menu then Example filters…, and select “Speedrunner Village (1.16+)” in the Examples Filters tab. 

### Spiral Iterator 1:N

A base search condition will start the search from world origin and search the areas defined. If you want to define additional starting areas for the base search for a condition, you can use spiral iterators to initiate searches from 1 or more points spiraling out from the center point of the search. 

The ratio selected will determine the density of the search area. 1:1 will apply the condition search to every block in the area defined. 1:1024 will select a block every 1024 blocks to provide the next starting point for the search condition that references the Spiral Iterator. 

The condition will be run against every point defined to be searched in that Spiral Iterator search area, and if any search point passes the condition, the whole condition will pass. This means if you use an exclude biome search, the condition will pass at the first area that meets the exclude. 

## Chapter 6: Others Conditions  {#chapter-6:-others-conditions}

The “Others” condition type has a few additional types of searches that either don’t specifically fall under another category, or there is a key difference in the way the search is processed that is helpful to separate it out. Some of these search types are very slow on their own, and so you generally want to use them later in the query, or earlier only in specific cases. 

### Spawn

This condition allows you to search for a world’s approximate spawnpoint and to use its spawnpoint as a reference for other conditions. Approximately half of all seeds have a spawnpoint within 31 blocks from the origin. Because of this, and the fact that calculating the world spawn is a slow process overall, in most cases it is quickest to assume the world’s spawnpoint will be near (0, 0\) and adjust one’s subsequent conditions from there.

This condition can be useful when running a search involving unordinary spawns (e.g., if one is looking for ocean/island spawns or faraway spawns), and in these cases where you may want to use the spawnpoint as a reference for other conditions to search for nearby features, or further solidify an island spawn with additional checks.  

In theory, a world’s spawnpoint could be up to 2687.5 blocks from the origin (specifically (1599, \-2160)), but in practice world spawns are nowhere near this far away. 

In Java Minecraft, the spawn algorithm will spiral up to five chunks in every direction away from its second-stage spawn estimate in an attempt to find a non-waterlogged block to spawn the player on; however, Cubiomes Viewer has no way of replicating this exactly, meaning this condition’s result will often be inaccurate. Versions 3.0 through 3.2.1 also contained bugs regarding this condition, though these have been fixed for v3.3.0.

### Slime chunk

Slime chunks are locations on the map where slimes can generate. This condition allows you to search for those specific locations. You can search for 1 or more instances in the area searched or select 0 to make sure that slime chunks are excluded from the search area. 

### Surface height

Surface height allows searching against the height of the overworld surface at a single block using a slider to select the range of values that will make the condition pass. You can select whether to look for value outside the range you select, or inside the range you select. 

When selecting your location, you will only pick a single X and Z coordinate, though note these coordinate values will be multiplied by 4 when determining the block to search. 

This is an approximate value based on the Depth climate at that point, and so will not reflect the true exact height of the world at that point. Furthermore, this can sometimes return higher or lower values than the maximum possible in-game. Extreme weirdness or erosion values can impact the calculated height to show these ranges outside the maximum possible. You can expand a Surface Height search using a spiral iterator to look for more than one point, but Surface Height calculation is already slower than other search types so this is another condition type you may want to put later in your condition list.

### First stronghold

Strongholds in Java, unlike strongholds in Bedrock Edition, generate in an iterative spiral; each stronghold’s position is determined in part by the position of the one before it, and so on. This is why searches for strongholds are generally extremely slow; to determine if a stronghold generates in a region, Cubiomes must first model every stronghold that came before it, as well as the biomes at each prior position to determine if each stronghold in the sequence would generate or not.

However, the very first stronghold that is generated, unlike every stronghold that comes after it, has its position (to within around 120 blocks) determined by the lowest 48 bits of the seed alone. As a result, not only can it be calculated in a fraction of the time required for strongholds in general, but when searching by 48-bit family blocks it can also eliminate entire blocks of 65536 seeds at a time like other structure conditions. As a result, if one has a condition dependent on strongholds (and does not mind false negatives in their search), it is usually extremely quicker for one to search based on the first stronghold compared to any other stronghold condition, or even before other structure conditions.)

## Chapter 7: Nether & End Biome Conditions  {#chapter-7:-nether-&-end-biome-conditions}

The Nether and End Biome Conditions work very similarly to the overworld “Biomes” condition, but instead will search only for the biomes that exist in either the Nether or End dimension. Once you understand how Biome searches work, setting these up is essentially the same. Each block traveled in the Nether represents eight blocks traveled in the Overworld. 

## Chapter 8: Quad Structure Conditions  {#chapter-8:-quad-structure-conditions}

Quad Structures is a special search type that can search for either 4 Witch Huts or 4 Ocean Monuments in a small enough area to allow for a farm to be set up where if the player is in the center of those structures, all the structures will have active mobs and spawning. 

All quad structure condition types multiply the coordinates by 512 and can run quickly across even large areas as the quad structures must fall on the corners of the spawn regions. 

Perfect quad-monuments do not exist, but some extremely rare structures get close. You can use the \>95% of \>90% to determine how close you want to try and search for. 

## Chapter 9: Basic Searches  {#chapter-9:-basic-searches}

For this section we’ll go through some very basic searches and build off those to find additional elements within a single query. 

### Village(s) with Cherry Grove

| Search \#1 – A Village ±250 blocks from World Origin |
| :---- |
| This starts with a single condition query to find a village within ±250 X,Z blocks of (0,0). Add a new condition, select Structure/Village. Set the “Within centered square of side” to 500\. Click Ok.  Using this condition will result in many seeds being returned quickly with a village near (0,0). Abort the search.  |

| Search \#2 –  Cherry Grove ±32 blocks, Village ±250 blocks from World Origin |
| :---- |
| Click “Add” to create an additional condition. Select Biome, “Biome 1:16”. Set “Centered square of side” to 4\. In the Biome selection click on the box beside Cherry Grove just once. A green \+ should show up. Click Ok. Running this search should result in a village ±250 X,Z blocks of (0,0), and a Cherry Grove within 32 blocks of (0,0). Abort the search.  |

| Search \#3 – Village near Cherry Grove |
| :---- |
| Double click on the Biome 1:16 condition. Beside “Location relative to”, click the drop down and select \[1\] Village X1 (-250,-250) (250,250). Click Ok. This will update the search to have the cherry grove show up with 32 blocks of the village instead of 0,0 when run. Abort the search.  |

| Search \#4 – Four villages ±250 blocks from World Origin with Cherry Grove in center |
| :---- |
| Double click on the “Village” condition. Update the “Instances within area” field from 1 to 4\. Click Ok. Running this query will result in 4 villages near (0,0), and Cherry Grove within 32 blocks of the Center of those 4 villages. When you search for a relative position against more than 1 structure, the game will find the average position of those structures and use the center point as the relative position for other conditions.  |

| Description | Conditions | Screenshots |
| :---- | :---- | :---- |
| **Village Within 250 Blocks from (0,0)** | \[1\] Structure: Village – Centered Square 500 | Appendix B1 |
| **Cherry Grove near (0,0), Village ±250 blocks from (0,0)** | \[1\] Structure: Village – Centered Square 500 \[2\] Biome 1:16 – Centered Square 4 – Cherry Grove | Appendix B2 |
| **Village near Cherry Grove** | \[1\] Structure: Village – Centered Square 500 \[2\] Biome 1:16 – Centered Square 4 – Cherry Grove – Relative to \[1\] Village | Appendix B3 |
| **Cherry Grove between 4 villages** | \[1\] Structure: Village x 4 – Centered Square 500 \[2\] Biome 1:16 – Centered Square 4 – Cherry Grove – Relative to \[1\] Village | Appendix B4 |

### Ocean at Spawn Searches

| Search \#5 – Lots of Ocean at World Origin |
| :---- |
| Add a new condition: Select Biome, “Biome 1:256”. Set “Centered square of side” to 6\. In the Biome selection click Exclude All. Then uncheck all \[-\] beside all ocean biomes and mushroom fields (leave the box beside those biomes empty). Click Ok. This search will look for ocean biome every 256 blocks near 0,0 usually resulting in large oceans. Abort the search and clear conditions.  |

| Search \#6 – Ocean at World Origin. Spawn within ±500 blocks in Old Growth Forest |
| :---- |
| Add three new conditions.  Biome 1:64. Centered square of side 8\. Exclude all biome types except any ocean and mushroom fields.  Others – Spawn – Centered square of side 1000\.  Biome 1:4. Centered square of side 0\. Location relative to \[2\] Spawn. Select “Match Any”. Select the three Old Growth Biome types (Old Growth Spruce Forest, Old Growth Pine Forest, Old Growth Birch Forest).  |

### Village Island Spawn – Optimizing Searches

| Search \#7 & 8 – Spawning on a Village Island |
| :---- |
| This search will use 6 conditions, however 4 will be very similar to each other. The 4 conditions will look for water to the NW, NE, SW, and SE of spawn.  Add two conditions to start.  \[1\] Others – Spawn – Centered square of side 300\.  \[2\] Biome \- Locate Climate Extreme. Select Custom with the following values {X1:25} {Z1:25} {X2:25} {Z2:25} – Continentalness Min \<= \-1900 – Location Relative to \[1\] Spawn Once you have created the \[2\] Biome condition, click the condition line to select it and right click to copy. Paste the condition 3 more times (right click paste x 3).  For the conditions you just created by pasting, double click each one and update the “Custom” values to the following.  Condition \[3\] \- {X1:-25} {Z1:25} {X2:-25} {Z2:25}  Condition \[4\] \- {X1:25} {Z1:-25} {X2:25} {Z2:-25} Condition \[5\] \- {X1:-25} {Z1:-25} {X2:-25} {Z2:-25} Add a Condition: Structures – Village – Centered square on side: 200 – Location relative to \[1\] Spawn. Start search: This will look for a spawn point and use that spawn point to find ocean in 4 corners around the spawn. This will often result in spawn point being on an island, though not every time. It will also look for a village close to spawn as well.  When running these conditions, look at the “seeds/second” in the bottom left-hand corner of Cubiomes-viewer. This is a slow query, but it should return results after a while. It could be minutes if you’re unlucky though. If you’re starting at seed 0, you will find the first result at seed 72652\.   |
| Now we will fix this query to return very similar results, but run significantly faster  Double click on the \[1\] Spawn condition and change the top drop downs to a Structure – Village search. Don’t change any other settings. Click Ok. Double click on the \[6\] Village – Structure condition and change the top drop down to an Others – Spawn condition type. Don’t change any other settings. Click Ok.  Run the new query and look at the seeds/second. It should have gone up a huge amount and results should be coming back quickly.  |

| Description | Conditions | Screenshots |
| :---- | :---- | :---- |
| **Only Ocean/Mushroom at 0,0** | \[1\] Biome 1:256 – Centered Square 6 – Exclude all biomes except All Ocean Types/Mushroom | Appendix B5 |
| **Ocean near 0,0. Spawn on Old Growth Forest** | \[1\] Biome 1:64 – Centered Square 8 – Exclude all biomes except All Ocean Types/Mushroom \[2\] Spawn – Centered Square 1000 \[3\] Biome 1:4 – Centered Square 0 – Match Any – Old Growth (Pine, Spruce, Birch) – Relative to \[2\] Spawn | Appendix B6 |
| **Spawn on Island with a village** | \[1\] Spawn – Centered Square 300 \[2\] Locate Climate Extreme – Custom X1:25 Z1:25 X2:25 Z2:25 – Continentalness Min \<= \-1900 – Location Relative to \[1\] Spawn \[3\] Locate Climate Extreme – Custom X1:-25 Z1:25 X2:-25 Z2:25 – Continentalness Min \<= \-1900– Location Relative to \[1\] Spawn \[4\] Locate Climate Extreme – Custom X1:25 Z1:-25 X2:25 Z2:-25 – Continentalness Min \<= \-1900– Location Relative to \[1\] Spawn \[5\] Locate Climate Extreme – Custom X1:-25 Z1:-25 X2:-25 Z2:-25 – Continentalness Min \<= \-1900– Location Relative to \[1\] Spawn \[6\] Structure – Village – Centered Square 200 – Location relative to \[1\] Spawn  | Appendix B7 |
| **Spawn on Island with a village (improved)** | \[1\] Village – Centered Square 300 \[2\] Locate Climate Extreme – Custom X1:25 Z1:25 X2:25 Z2:25 – Continentalness Min \<= \-1900 – Location Relative to \[1\] Village \[3\] Locate Climate Extreme – Custom X1:-25 Z1:25 X2:-25 Z2:25 – Continentalness Min \<= \-1900– Location Relative to \[1\] Village \[4\] Locate Climate Extreme – Custom X1:25 Z1:-25 X2:25 Z2:-25 – Continentalness Min \<= \-1900– Location Relative to \[1\] Village \[5\] Locate Climate Extreme – Custom X1:-25 Z1:-25 X2:-25 Z2:-25 – Continentalness Min \<= \-1900– Location Relative to \[1\] Village \[6\] Spawn – Centered Square 200 – Location relative to \[1\] Village  | Appendix B8 |

## 

## Chapter 10: Optimizing Search Conditions  {#chapter-10:-optimizing-search-conditions}

### Faster searching

There are many ways to optimize your search conditions to approach the fastest possible search for what you want to find. This section will include some methods to try depending on the type of search. There are many nuances to look out for, such as higher seeds per second doesn’t always mean a better search. You may want to try to estimate returned seeds per second/minute/hour or determine how often you are getting a good result to determine if you improved your query. Here are some examples of things you may want to look at.

* Have you created any impossible conditions (Biomes that can’t be next to each other)?  
  * Are your conditions ordered to rule out invalid seeds faster (E.G. structure searches close to spawn can rule out seeds faster than wide biome searches)  
  * Are your biome searches too dense? (E.G. using a 1:4 when a 1:64 will work just as well)  
  * Can your biome searches be replaced by climate parameter searches?  
  * Are you able to narrow your search closer to world origin to be faster, or widen your search using Spiral Iterators while returning more seeds over the same timeframe?  
  * Can you utilize a structure search that can only occur in the same conditions as your biomes (E.G. if you want Jungle, find a Jungle Temple)?  
  * Are some of your conditions significantly slowing the search down, and if so, can you pull those conditions out and then set up a second search that only runs on the seeds that meet your other conditions?  
  * Can a slower condition reference a faster condition to ensure the faster conditions exclude seeds before trying to run slower conditions?


Conditions are checked from the first conditions displayed in the list to the last, though it appears some conditions will run concurrently and can slow down a search even if the slower condition is lower in the list. The number beside the condition is a label to allow for that condition to be referenced by other conditions but does not set the order for checking the conditions. 

### Ordering Conditions for Speed

Once you have set up the conditions you wish to search, start your search to check the Seeds/Second value to determine how quickly your query is excluding seeds that did not pass your conditions. Stop the query, then drag the conditions up or down the list to create a new order for the condition checks. This will potentially change the seeds per second of the query. Assuming you didn’t change your conditions, changing the order to get the fastest Seeds/Second should provide the best version of that specific set of conditions for searching against. There may be faster methods of setting up the same search using different conditions, however.  

* The seeds per second is generally an indication of how quickly the query can rule out a matching seed. High seeds/sec does not always mean a better query. You could be eliminating all seeds due to impossible condition sets, but still have a very high seed per second. Try to determine your “matching” seeds per minute (or hour/day depending on how complex) for one query vs another to determine the efficiency of your query.   
  * Conditions that reference another condition must be below the referenced condition.   
  * Different search criteria are faster than others. Structure searches are often faster than biome searches. The rarer the structure, the faster the query can rule out seeds to provide you with a match. Try out rare structures high in the condition list.   
  * Climate parameters can also be faster than biome search and locate climate extreme can be faster than a climate parameter search. If it’s easier to create a climate parameter search, it may be worthwhile to find a method.   
    * Easy climate parameter search examples include Mushroom Biome always generating when Continentalness \<= \-10500, Ocean or Mushroom Biome generating when Continentalness \<= \-1900. Hot biomes (Desert, Badlands, Eroded Badlands, Wooded Badlands, Warm Ocean) generating when temperature \>= 5500

### Impossible Conditions {#impossible-conditions}

It is easy to create impossible conditions or condition sets, so you may need to do some research to determine if your search is even possible. Some examples of things that may create an impossible condition set are below.

*  Strongholds \< 1280 radial blocks from World Origin 0,0 (Specific to Java which is what Cubiomes is searching against)  
  * Most large structures (Villages, Templates, Mansions etc.…) cannot generate between X: \-1 to \-143 and Z: \-1 to \-143  
  * In version 1.18+, Hot and Cold Biomes within approx. 400 blocks of each other.   
  * Meadow/Cherry Grove directly next to Ocean  
  * Lush cave underneath Cherry Grove (differing Humidity)  
  * In version 1.18+ Mushroom Biome next to anything except ocean.   
  * In version 1.18+ Spawning on Mushroom Biome (May be technically possible but no one has ever found one)  
  * Villages within 125 blocks of Pillager Outposts (specific to Java)

## Chapter 11: Seed Analysis {#chapter-11:-seed-analysis}

Once you have found seeds, you can perform additional analysis on seeds to find more properties or perform additional condition checks against them without creating a new query. You can analyze seeds you have listed in the matching seed list, or the seed you have up as listed in the top of the interface under “seed:”. 

### Triggers

Triggers allow you to find seeds that match the current conditions and provide a listing of locations for where the match occurred that caused the condition to pass. This allows you to find the locations of the structures or biomes that matched conditions without having to try and find it manually in the seed. 

You can also use the trigger to run additional condition checks against the current list of seeds. After you have stopped your initial query, turn on or add new conditions and run the trigger analysis against the Current Seed List to see if any of the existing seeds match the new conditions. 

### Biomes

The biomes analysis tab has two different analysis types, “Locate” and “Statistics”. Both these two types allow you to search against the biomes in a specific area and provide back details about either a single biome, or all the biomes. To choose the area you want to search against, you need to define a square/rectangular area by choosing X and Z values at 4 different points. This can be done by either typing in an X1, X2, Z1, and Z2 value, or by moving the map to the area you want to search and clicking on “From visible”. This will automatically fill in the four values to encompass the area shown on the map. 

#### *Locate*

This analysis allows you to select a single biome type and a minimum area size to look for biomes of a specific size in the area you specify. This works much like the “Locate Biome Center 1:4” search condition but will provide an output of the area side of the biome, and the approximate center of that biome. This will allow you to compare the sizes of biomes in different seeds. 

You input the area size you are looking for and the border tolerance, and the tool will search for an area that meets that criterion in either the current selected seed, or the list of matching seeds from the Search tab. 

There is currently a bug in 3.2.1 that will provide back incorrect values for the area size by multiplying the true number by 4 or 8\. While this will hold true against all seeds so you can still compare area sizes, you may want to run a separate search in the “Statistics” tab to get true area size numbers. 

#### *Statistics*

This analysis allows you to register all biomes in a defined area and provides the block count of those biomes. You can choose to search every block in that area to have more precise block counts, or you can choose a ratio which will search every 1, 4, 16, 64, or 256 blocks in that area. This method will allow you to get an approximate comparison of biome distribution in that area and allow you to compare different seeds very quickly.

Results are returned in a list with the seed on the left, and each biome appears as a column header with a value listed for how often that biome shows up for that ratio. 

I have found using the 1:64 search to be extremely useful when searching for instances of a single large biome such as Mushroom or Dark Forest. It allows for very quick analysis of many seeds, and the list provided back can be quickly sorted by biome by clicking on the column header to see the largest seeds at the top. 

One downside (possible bug) to this analysis tab is that you cannot click on the seeds and have them show up in the map window, and the display does not always show the full seed number. You might need to export the analysis and pull up the results in a txt file to find the full seed numbers. 

### Structures

Much like the Statics tab for biomes, this analysis type allows you to search for structures in a defined area. You can search for all structures, or just the ones you have selected on the map to get the count of structures, the locations of those structures, and additional details that may be relevant to that structure type such as Village type. 

## Chapter 12: Session Files  {#chapter-12:-session-files}

Session files allow you to save your conditions and matching seeds so you can keep the progress of your searches or refer to previous condition sets for new searches. This also allows you to share your searches with other seed finders. 

Session files are text files that save the Cubiomes-viewer version you created the file in, any additional settings that might be relevant to the search, a text notation for all the conditions you created and a listing of seeds from the matching seed list. 

Session files from one version may not work in another version if some of the features changed between those versions. If you have a session file with “Location climate extreme” biome condition, but you pull it up using a version without the “Locate climate extreme” condition type, the session file will fail to load. 

Cubiomes-viewer does have some auto-save settings for session files when you close the program, or after so many minutes. When cubiomes-viewer is opened, the last auto-saved session file will be loaded. 

There are some conditions with limits in the user interface that can be changed to higher or lower values than can normally be accepted by editing the session file. This guide will not go into how to edit these files, but wanted to address that it is possible and has been used to find specific features in earlier versions that were not otherwise possible using Cubiomes-viewer. 

## Chapter 13: Settings  {#chapter-13:-settings}

### File Menu

#### *Load Session* 

Load an existing session file that contains predefined conditions and matching seed list. 

#### *Save Session*

Save a session file for the currently defined conditions, some base settings (such as Version or Search Type) and matching seed list. 

#### *Load Filter Preset* {#load-filter-preset}

Opens the Preset Filter menu where you can Save or Load a condition filter. A filter acts like a session file that only saves conditions and version and saves in the menu rather than creating an external file that needs to be loaded. You can also add a description to your filter to reference when selecting which filter to load. There are some examples of preset filters that are pre-populated by Cubitect, or you can create your own with the “Save Current Filter” button. 

#### *Search Seed List*

This will update your search type to “seed list from a file” and open a prompt to load a file from your computer. You will want to load a txt file with the listing of seeds on each line. 

#### *Search full Seed Space*

This updates your search type to 48-bit family blocks. 

#### *Quit*

Exit the program.

### Edit Menu 

#### *Copy Seeds from List*

This copies the list of seeds in the Matching Seeds list into your clipboard. This can also be accomplished by right clicking on the list and selecting “Copy list to clipboard”. 

#### *Paste Seeds into List*

This pastes any numbers in your clipboard that would work as seed numbers in Minecraft into the Matching Seeds list. 

#### *Add shadow for all seeds*

Only works for versions 1.17 and below. A shadow seed is a seed that contains all the exact same biome layout as another seed, but everything else about the seed is different (terrain height, structure placement etc..). This can be used to find the shadow seeds for your matching seeds. 

#### *Advanced World Settings*

Allows for the addition of structure salt to deviate from standard Minecraft structure generation. This could let a server admin who added structure salt to their seed to view a map of where structures are located in that seed. 

#### Preferences

##### GUI Style

This setting allows you to switch between Dark mode and System default. 

##### Biome Color Customization {#biome-color-customization}

This allows you to change the default color for all the biomes, or to dim biomes so the other biomes stand out more. Once you have made changes to the colors, you can also save your changes as a color profile. If you have an exported color profile, you can load that file by clicking the … below the Edit biome colors button. 

##### Maximum Structure Zoom  {#maximum-structure-zoom}

Edit map visibility limits: This value allows you to change the number of zooms you can go out before certain structures disappear from the map to only show biomes. I might use this if I want to find structures that are typically spaced far apart like Woodland Mansions, or if I want to find clumps of structures such as Ancient Cities that indicate an area of mountains. 

##### Custom Grid Spacing

The default grid spacing starts at 128 blocks and will expand out when scrolling out at 4 times the previous spacing. Lines start 128 blocks wide, then 512, then 2048 etc. The Custom Grid spacing allows you to change the starting width of the grid spacing, and the multiple at which the grid will move out as you zoom out. To reset the grid to auto-update in spacing with zooming enter 0 to go back to default.  

##### Map cache size

May be useful to increase if you’re searching across a large portion of a single map, but typically default should be fine. 

##### Threads for map

Scrolling through lots of seeds can add strain to your CPU load on your computer to generate the maps quickly. You can change the amount of CPU resources used for loading the map features. 

##### Outline known bounding boxes

When zoomed in enough, red boxes will appear around structures showing the bounding boxes of that structure. For example, in Villages this would be the starting piece.

##### Smooth Map Motion

With this feature turned on, when dragging the map in a direction, when you let go of the mouse the map will continue to move and slow down smoothly rather than stopping immediately. This allows you to “fling” the cursor and move the map far distances quickly.

##### Search – Maximum Number of Matching Seeds

This value controls the point at which cubiomes-viewer will stop looking for matching seeds after it finds a certain number. This is to make sure you don’t use all your memory or crash the program if it finds too many matches very quickly. You can update this value if you want the program to look for more or less seeds before it stops. 

##### Session

This relates to the auto-saving of sessions. 

###### Restore Previous session at launch

If this is checked, when you close cubiomes-viewer the system will create a session file save for conditions and matching seeds from the point when the program is saved. When you open cubiomes-viewer again, the conditions and matching seeds will autoload from what was previously showing at last close of the program. 

###### Autosave every x min

This will auto save a session file every set number of minutes that will restore when opening cubiomes-viewer. You can open more than one instance of Cubiomes-viewer at one time, and when you open a second instance the program will load the last auto-saved file it can find. Also, if Cubiomes-viewer crashes for some reason, the last auto-saved file will be loaded when opening the program again. 

##### Export

For analysis files that are exported out of Cubiomes-viewer. For CSV delimited files, you can designate what character separates the values. If you export the biomes-statistics, when all the biomes are listed with their count next to the seed numbers, they will be separated by the character you input in CSV Column Separator. If there are any export names or values with a space or a character used at the column separator, the CSV cell quotation can be set to only use a text designation (single quote or double quote) when needed. Or you can set it to always use a text designation for each cell. 

### Map Menu

#### *Previous seeds*

This provides an additional list of the most recent seeds you have viewed in Cubiomes-Viewer. When you select this option, an additional list will appear to show you seeds you have recently opened. 

#### *Open Shadow Seed*

Each seed for Java Versions 1.1-1.17 has a shadow seed, which is a seed with the exact same biome layout as their shadow, but with different terrain, structures. This option pulls up the shadow seed for the seed you have currently selected. This option is unavailable for open seeds in V1.18+

#### *Undock Map/Redock Map*

Selecting Undock Map will create an additional window with the map that can be moved around separately from the base interface. It will be on a layer above the base cubiomes-viewer interface, and to change the seed or structure display, you will need to click on the options in the base interface. To dock the map window back to the base interface, go back to the menu and select “Redock Map”

#### *Go to…*

Same as Go to coordinates when right clicking on the map. Explained in [Chapter 1: Map, dimension, and structure display](#map,-dimension,-and-structure-display).

#### *Take screenshot*

When selected, opens a “File Save” prompt to save a screenshot of just the map portion of the interface. This does not include seed information. 

#### *Export biomes as image…*

This option pulls up an additional window with options for exporting one or more images of the terrain of a seed. 

##### Seed(s)

You can select either the Current seed, or the Matching Seed List. When exporting, it’s good to verify the number of images that will be created as choosing the Matching Seed List can create many separate images. 

##### Scale (pixel:block)

This allows you to select a ratio of pixel to block size with 1:1 being the smallest and 1:256 being the largest. Choosing a large multiple with a “Size of image tiles” can make for a large area as the pixel size of the image will remain the same, but each pixel will represent a different size of area from the map. A 512 image tile with 1:256 means 131,072 x 131,072 map area. 

##### Heightmap

Images exported can be of the flat terrain of the Biome Scales map layer,  or an image using one of the four Heightmap options (A.K.A Approx. Surface Height in the Layers menu). 

##### Export Directory

Choose the directory where you want to export the image(s). 

##### File Pattern

When the image file(s) is created, you can assign a name based on the seed, and the X/Z values chosen. The format is listed below the field, and you can add any static file name characters as well. 

##### Area in blocks (bounds are included)

Input the area you want to generate an image of. This will export the rectangular area you define using the 4 X/Z points. “From visible” will auto define the bounding area by what is displayed on the map. 

##### Split image into tiles

This splits the map into pre-defined tile areas based on the size you select, with the first tiles northwest corner starting at (0,0). 512x512’s first tile is from (0,0) to (511,511). 

For the range defined in the “Area in blocks”, all tiles that are included in that range will be exported. So if you select (-520,-520) through (200,200), you will get 9 tiles exported since you have selected an area with points in all 9 of those 512x512 tiles. Depending on what you select for Background color, you will either get full tiles with “Fill Background by Expanding Area”, or partial tiles with either Transparent or Black. 

**CAUTION**: In v3.30, if you select “Split image into tiles” and define a Scale for the same export, the tile size that is used will be the Scale times the Split image definition. So 512x512 with a 1:16 scale will make a map of ±16384 and scale it down into a 512x512 pixel size. It may take a long time for cubiomes-viewer to generate that image based on such a large map area, even if the image size isn’t large. At the maximum 4096x4096 with a 1:256 scale this will generate images using 1,048,576 x 1,048,576 map area condensed into a 4096x4096 image size. 

##### Overview

This will provide information related to the seed(s) you are exporting. You will see the version and dimension, total Y height (based on the Y value dropdown selection on the main interface) and the number of seeds (always 1 when Current Seed selected). You can also use this to determine the pixel size of the files you are exporting, as well as the number of files that will be generated. This can help you avoid trying to generate too many files by accident. 

#### *Biome colors…*

This is the same as [Biome Color Customization](#biome-color-customization) in Edit \-\> Preferences

#### *Structure zoom limits…*

Same as [Maximum Structure Zoom](#maximum-structure-zoom) in Edit \-\> Preferences

### Layers Menu

In the “Layer” menu, you will find a listing of map settings to change the map to display different elements. 

#### *Biome scales*

The default map view provides a flat 2d view of the world. 

#### *Climate Parameters*

All the climate parameters except Depth display Perlin noise values using a black and white heatmap with white being the highest values, and black being the lowest. Each climate parameter has additional octave values which can be found in “Display options…”

#### *Depth*

Provides an approximate calculation of the surface height, which white being the highest points and black being the lowest but is not Perlin noise and so is less gradient. 

#### *Approx surface height*

A grayscale height map is the default value for Approx surface height. There are 3 other options within Approx surface height, however you will only see these options when selecting “Display options”. 

##### Shaded biome map

Provides shading to give a 3D effect on the map to show height and depth. If you hover your cursor over an area, you can see the calculated terrain height at a given X,Z point.

##### Contours on biomes

This map is the Biome scales map but with contour lines to show the approximate elevation of a given area. 

##### Shaded with contours

This map is a combination of the Contours on biomes map with the Shaded biome map. Contour lines on a shaded map to represent height and depth values. 

#### *Structure potential (48-bit)*

This map shows where structures have the potential to generate for a given 48-bits. This does not represent where the structures were generated for a given seed. 

### Help

#### *Example filters…*

Example searches provided by Cubitect. Can also be accessed in File Menu \-\> [Load Filter Preset](#load-filter-preset)

#### *About*

Provides the version number, licensing, and legal information about cubiomes-viewer. 

## Chapter 14: Putting It All Together  {#chapter-14:-putting-it-all-together}

In this guide I have tried to explain how most of the functions of cubiomes-viewer work so that you may understand how you might be able to utilize the tool to find the types of seeds you want to find. However, to put together a good search, you want to take what tools are available to you and figure out how best to formulate a query that will find the seeds you want, in the fastest way possible. 

I don’t want to disillusion you that I might know the fastest way to put together any specific search, but I have picked up tricks along the way that have helped me formulate different methods of searching for what I want to find. I want to share the concepts for ways to approach a search, and then you can take those and try out different methods to see what works best for you. This section will focus on a few specific types of searches and ways to build a query. 

### Islands

For this guide, I’ll define an island in several ways. 

* Land Biome surrounded by Ocean  
  * These are probably what most people think of with regards to looking for an Island, and the setup for finding one can be fairly simple. Generally speaking, you want to find lots of ocean biome, with a little bit of land biome.   
    * The first method of searching for these involves creating a circle of conditions around a center point (Spawn, high Continentalness, land biome, land structures, world origin etc..). I would do this by creating 4 or 8 conditions (maybe more if looking for continents) to limit the size of the island by defining where I want ocean to be. If you are looking for smaller islands, I find it good to use “Locate Climate Extreme'' for Continentalness \<-1900 at single points. If you want bigger islands, you could use a “Climate Parameter'' with Confined Continentalness \<-1900 with large areas, or biomes excluding all but ocean/mushroom, or an area with lots of shipwrecks (I find 4 or 5 in a 512 square block area to be sufficient).   
    * The next method I allude to in the previous search type. Instead of trying to find points or areas of ocean surrounding a central point, you could just look for lots of shipwrecks in an area where the spawn point exists.   
* Land Biome surrounded by River  
  * As with many types of biomes in Minecraft, you can often find circles of river forming in various locations in a seed. These circles can show up anywhere, even on ocean islands that can generate an island of land biome in the middle of them.   
  * To search for these, I use the same principle as looking for an ocean island with surrounding points. Define what you want as the center point for where the island will show up, then look in 4 directions to find river. To do this I usually define custom location searches that only use either X or Z values and have one set be negative (north of west), and one set be positive (east and south).  
    * Some defined central point. This could be a Biome 1:4 search for a specific non-water biome, or a structure, or spawn.   
    * Biome 1:16 Custom Location X1: \-6 X2: \-2 – Match any River/Frozen River.   
    * Biome 1:16 Custom Location X1: 2 X2: 6 – Match any River/Frozen River.   
    * Biome 1:16 Custom Location Z1: \-6 Z2: \-2 – Match any River/Frozen River.   
    * Biome 1:16 Custom Location Z1: 2 Z2: 6 – Match any River/Frozen River.   
* Ocean biome that generates above ocean level  
  * While small islands showing up in the ocean that aren’t associated with a land biome type are common in Minecraft, Cubiomes-viewer is not necessarily suited for searching for these types of islands. While there is terrain height and depth calculation, for ocean these are typically displayed as static heights by ocean type rather than fluctuating up and down. 

### Mountain Circles

Mountain circles form in fairly specific conditions and depending on what you’re wanting to look for can be accomplished by a few methods. Look to finding river islands as an example. 

* First, you can find some central point (I generally use world origin or a structure), and then look for Peaks in 4 different directions surrounding that central point.   
* The other method is using climate parameters. Low erosion means you will find high peaks in an area, and low or high weirdness means there will be strong peaks and valleys which combined create the conditions for mountain circles. A very simple search near spawn for low erosion, and high or low weirdness can find mountain circles very quickly. 

### Strongholds

Strongholds can be challenging to search for as the calculation to determine their location is more complex than other structure types. This typically means you want to search for strongholds later in a query, but there are times where you might look for them earlier. 

For something like a spawn near a stronghold, generally I first create conditions for spawn to be far from 0,0. This would involve excluding all biomes except for ocean out a wide distance (remember Strongholds must be more than 1100 blocks radius from 0,0). Then I perform a search to look for the First Stronghold, as this calculation is easier on Cubiomes than looking for any Stronghold. After that I set up a condition to look for a stronghold close to the first stronghold (to get a more exact location), and then finally look for spawn near the Stronghold. 

### Large biomes

To find a large quantity of a single biome, I generally put together a few condition types. The first is to just find 5-10 single points in an area of that specific biome type. This can be accomplished by using climate parameters (locate climate extreme is great for Mushroom Fields as you can just set it to look for Continentalness \<-10500), or just single points of biome 1:4 searches. For the last condition in this search, setting up a “Locate biome center” so I can define a minimum size. Start with a smaller area definition and work up to figure out a good balance of getting returned seeds without slowing your query too much. 

### All Biomes

It’s easy enough to throw in a search condition for all biomes in a specific area, but this condition can be very slow. To speed up the process of finding all biomes, I use one of the Sample filters that Cubitect included with Cubiomes-viewer (Biome diversity 1.18+). This condition looks for the full range of climate parameters needed for all biome types to exist. While this doesn’t guarantee that all biome types will show up, you can combine it with an all-biomes condition. Remember to uncheck dripstone, deep dark, and lush biome types as they do not show up on the surface, and you’re pretty much guaranteed to get them all in a wide enough area with all biome types anyway. 

### Sinkholes

Sinkholes are formed by a generation bug that existed in Java 1.18, 1.18.1, 1.19, 1.19.1 and 1.19.2, and still exist in Bedrock. Since there is biome parity in Bedrock and Java, you can search for them in cubiomes-viewer and pull them up in a current Bedrock version to see what forms. It’s harder to find large sinkholes in Bedrock, but some good ones still exist and can be fun to find, especially with Villages nearby that can create large floating aquifers.

To search for sinkholes, you just want to find areas of very low or very high weirdness. The best sinkholes start forming at around ±19k in Java, and ±20k in Bedrock. I generally structure my search using a Spiral Iterator out either 500 or 1500 blocks (using a higher ratio like 1:256), then look for Low/High Weirdness (±13k), then look nearby for very high/low weirdness (±20k). This is best done using Locate Climate Extreme.

Sinkholes do not generate in either oceans or in mushroom islands, even if the Weirdness values are extreme. There will be false positives that you will have to sort out by checking the seeds one by one. You could add a condition that checks the biome in which the sinkhole is generated, but this is not really necessary given the rarity of sinkholes.

Use the Approx. Surface Height – Grayscale  (Alt \+ Y and Alt \+ 1\) to find the potential sinkholes on the map.  You will see red areas where the Approx. Surface Height is below y \-64 (bedrock level) which is responsible for the generation of sinkhole. You can quickly switch to Approx. Surface Height – Shaded with contours by pressing Alt \+ 4 to visualize which biome the sinkhole is in.

### Big Mountains

Large mountains can be found using several methods. Mountains show up in areas of low erosion, so searching for low erosion helps. Next, you can create many condition points near world origin that you want to be peak biome to find the largest mountains (or use locate biome center).


## Appendix {#appendix}

### Appendix A

| Name | Author | Description | Conditions Explained | Link(s) |
| :---- | :---- | :---- | :---- | :---- |
| **Survival Islands** | Jereaux | Small, isolated islands in a large ocean that your character spawns on. | 8 points of low Continentalness (Ocean) 1000 blocks from (0,0) Finding Spawn within 750 blocks of (0,0) 8 points of low Cont. 360 blocks from spawn 4 points 700 blocks from spawn with 640 block wide areas of low Continentalness (Reference points for defining new search area) Higher Continentalness at spawn point (not-ocean) Disabled Optional Temp Check for Non-Frozen | [Isolated Island Survival Spawn](https://docs.google.com/document/d/1GD6H_pzGD1uRSDXDPP6G8lTD-vGzJWibuxiBIkL1l1E/edit?usp=sharing) |
| **Continent Islands** | Jereaux | Continent islands are large islands surrounded by ocean | 4 Points of Low Continentalness at ±(1800,1800) corners 12 areas of 1000 blocks wide looking for 5 shipwrecks (Reference points for each defining areas in a large square around (0,0)) | [Continent Island Finder](https://docs.google.com/document/d/1_GfjG5jAbpcwC10ndFVBOKjD7kHN2W2f8bMC5SDfmkc/edit?usp=sharing) |
| **Mountain Islands** | Jereaux | 2 Queries. Find mountains with lots of water. Then additional filters against the seed list created by first search.   | Finding The Mountain Islands (Step 1\) 29 Shipwrecks within 1250 blocks from (0,0) Finding Spawn within 1350 blocks of (0,0) 4 Reference Points to define 4 new points for setting a search area. 4 areas of excluding all biomes except ocean/mushroom Match Any biome search for any Peaks within 256 blocks of Spawn. Additional Filters (Step 2\) Finding Spawn Dense spiral iterator 1:4 out to ±320 Blocks Surface Height against Spiral Iterator for Mountains over Y195 Disabled: Lush Caves at Sea Level Disabled: Stronghold ±400 blocks from Spawn | [Mountain Islands – Step 1](https://docs.google.com/document/d/1kghlLlY86KoMk3XlWKq25xmK25bn_4QAdql7L8FHRcE/edit?usp=sharing) [Mountain Islands Additional Filters– Step 2](https://docs.google.com/document/d/1Kw72ePx7y23lQDAbv6WSjmTrdGI97kW7kFp22J_gifA/edit?usp=sharing) |
| **Large Mushroom Islands** | Jereaux | Query to find very large mushroom islands at world origin.  | 4 Octave Continentalness Checks for Low Cont.±256 Blocks from (0,0) 4 Low Cont. (at Mushroom generation levels) checks at ±256 Blocks from (0,0) 400 Blocks of Confined Low Continental check (allows for Mushroom and some Deep Ocean) | [Large Mushroom Islands](https://docs.google.com/document/d/174if0wZG-q1l6ysMMb0d-ZmFo0giRC9eDrdZJg-kkdc/edit?usp=sharing) |
| **Large Mountains** | Jereaux | Finding wide areas of only peaks.  | Spiral Iterator 1:64 ±256 blocks Low Erosion check against Spiral Iterator Area Exclude all biomes except Peaks for ±144 blocks from Low Erosion point | [Giant Mountains](https://docs.google.com/document/d/1pH0NMW2dkcO8iXbclQQGFQIsASpC_WpORjOpbfkAKrs/edit?usp=sharing) |
| **Large Cherry Grove** | Jereaux | Finding large cherry grove biome near world origin.  | 13 Points of High Weirdness Check ±128 blocks from (0,0) 13 Biome checks for Cherry Grove ±128 blocks from (0,0) | [Large Cherry Grove](https://docs.google.com/document/d/1vwPvw7JFpEmm6xRp6BmziJg1BFpWreZ24xQe_COUEvs/edit?usp=sharing) |
| **All Biomes near Spawn** | Jereaux | This looks for the full range of climate parameters that all biomes can spawn in, then all biomes within a range from (0,0).  | 10 Octave Checks for a wide range of each Climate Parameter 10 Climate Parameter checks for the full range needed for all biomes to spawn. 3 Biome searches encompassing all biomes. Searches for rarest biomes first.  | [All Biomes Within 1600 Square Blocks](https://docs.google.com/document/d/1szmTHuyf6n-jv26PUlFCfQWL4rUCTnb6zYrgpsXRd3c/edit?usp=sharing) |
| **Windswept Mansions** | Jereaux | Woodland mansions directly next to windswept terrain that can often produce very tall mansions. | Woodland Mansion \+112 from (0,0) 4 checks for Match Any Windswept Savannah or Forest surrounding Mansion. Check for Windswept Savannah near Mansion Note: You will need to log into each seed to see the height of the structure.  | [Windswept Mansions](https://docs.google.com/document/d/1bDkEhEo76zwEst0YwrwOIaUbj-59y7NxuOTrhQI0rT4/edit?usp=sharing) |
| **Mountain Circles** | Jereaux | This finds peaks that generate surrounding a non-peaks biome.  | Low erosion check OR Logic Gate 2 checks for Either High Weirdness or Low Weirdness assigned to OR Logic Gate Checking for Higher Cont (matching parameters aren’t over ocean) | [Mountain Circles](https://docs.google.com/document/d/1KURYkdBs-yxw1COsspb49eycxEdslSrD2EuR7wopByY/edit?usp=sharing) |
| **Mountain Circle Lakes** | Jereaux | This looks for conditions that produce peaks surrounding an area of land that dips down below sea level. Best run in 2 steps.  | Part 1 Search – Run First 5 Conditions.  Same as Mountain Circles, but more extreme climate parameter values (8 disabled conditions). Run for a while (will return lots of results).  Part 2 Search – Enable additional 8 conditions. DO NOT START SEARCH Go to “Triggers” tab. Set Seeds \-\> From matching seeds list. Analyze. No Ocean ±200 blocks from (0,0) Spiral Iterator to ±96 blocks Finding a patch of No Deep Dark under the mountain circle 4 searches for peaks surrounding patch of No Deep Dark Search for Y level beneath Water generational level.  | [Mountain Circle Lakes – 2 Part Query](https://docs.google.com/document/d/1nNqYNGIcscsqCF4HygfjvebE9-T6jWJgG4EGZwFmenw/edit?usp=sharing) |
| **Mountain Circle Mansions** | Jereaux | Finding peaks near world origin that go up to the biome generation limit (Y:256) | Mansion check \+400 blocks from (0,0) 4 checks for Match Any peaks surrounding Mansion out 240 blocks from Mansion.  | [Mountain Circles with Mansion](https://docs.google.com/document/d/1vNljVJsUMUOep75oVBqCsWZdysMTfnJ4QZ1zc8d35oM/edit?usp=sharing) |
| **River Islands** | Jereaux | River islands form when a river goes in a circle around another land biome.  | Exclude All Ocean and River ±12 from (0,0) 4 checks for river in different directions 32 to 83 blocks from (0,0) Surface check at (0,0) for Y above 65 | [River Islands](https://docs.google.com/document/d/1PrBbEozbn9mgFlhdUAdHN49jE6xOO_X61HJZAbSsMdU/edit?usp=sharing) |
| **Sinkholes \- Biome Lakes** | Jereaux | 2 different searches. Finding sinkhole conditions (only generate 1.18-1.19.2)  | Sinkholes at World Origin 3 OR Logic Gates 3 Sets of OR Logic Gate looking for High OR Low Weirdness at different Weirdness octaves Sinkholes out to 512 Spiral Iterator out to ±512 4 conditions for High Weirdness at different Weirdness octaves Disabled: 4 Conditions for Low Weirdness at different Weirdness octaves | [Sinkholes by World Origin](https://docs.google.com/document/d/12NYKeD1Uofe7-bTzzbKTiRetv4PXnrvud1O8RFiXIGs/edit?usp=sharing) [Sinkholes to 512 Blocks Out](https://docs.google.com/document/d/1d6nOfh5kv4B83D0HpFoZKJzFgcBr0Lne31_CGwVkiX8/edit?usp=sharing) |
| **Big Oceans** | Jereaux | This searches wide areas of ocean biome.  | 32 points of Continentalness octave low Cont. at same points where 1:256 would check. 1:256 biome check for exclude all but ocean out ±1280 | [Large Oceans](https://docs.google.com/document/d/19F9vkylHxmQ35ECrZuVTw5xQIBO3MC8Qpl7_CHMS9AU/edit?usp=sharing) |
| **Stronghold Spawns** | Jereaux | This searches for large oceans so that the spawn point can be far from world origin, and then looks for a spawn point near a stronghold.   | 16 checks for points of low Continentalness out to ±768 from (0,0) Exclude all but ocean/mushroom check out to ±768 from (0,0) (Not Logic Gate). Spawn is NOT 1100 radial blocks from (0,0) Other – Find First Stronghold ±1600 blocks from (0,0) Stronghold search against First Stronghold for more accurate structure generation location Checking for spawn within ±200 blocks from Stronghold | [Spawn near Stronghold](https://docs.google.com/document/d/1uic4Y3IvwCdKFj24ZD7EK_YkZu7-PotSiyIURmGGKgE/edit?usp=sharing) |
| **Lots of Ancient Cities** | Jereaux | This looks for many ancient cities near world origin.  | Low erosion check at (0,0) – (For Mountains) Four Ancient Cities ±512 from (0,0) 22 Ancient Cities ±1024 from (0,0) | [Lots of Ancient Cities](https://docs.google.com/document/d/1bY1KERw1v-p5aFH8HIpy2Y_VuG830U7_VJZGQmkg3Sg/edit?usp=sharing) |
| **Windswept Ice Spikes** | Jereaux | This looks for ice spikes biome next to windswept gravelly hills that can sometimes produce very tall ice spikes.  | Low Continentalness check at (0,0) – Seems to have an impact on Windswept Gravelly Hills generating to very high Y values Biome check for Windswept Gravelly Hills and Ice Spikes to ±12 from (0,0) | [Windswept Ice Spikes](https://docs.google.com/document/d/1tArbU8XEzRm5Kq3SB2PKISQZQFXd1wBjVtX4PND_g7w/edit?usp=sharing) |
| **Structure Islands** | Jereaux | A search for structures generating on islands.  | Check for Woodland Mansion ±500 blocks from (0,0) – Can change to any structure. 2 checks for shipwrecks between ±512 and ±1024 blocks from structure Disabled: Check for spawn near structure | [Structure Island Seeds](https://docs.google.com/document/d/1abTXdQnh5Upql_owIqIPoO2YXgFqAYWrJhLw6WhWvkU/edit?usp=sharing) |
| **Abandoned Village in Mangrove** | Jereaux | A search for an abandoned village surrounded entirely by Mangrove Swamp.  | Check for village \+100 blocks S/E from (0,0) 4 checks in different directions for Mangrove, each 32 to 80 blocks in a single direction from the village. | [Mangrove Abandoned Villages](https://docs.google.com/document/d/19QVfe81MZq4aaSlYfuEnX5vhWw4p1Jpx2YalNp1wWKw/edit?usp=sharing) |
| **High Lush Cave Islands** | Jereaux | Search for islands with Y128 Lush Caves | 20 checks for low Continentalness ±512 blocks from (0,0) Recenter last check to start at (0,0) – The cave check wants to happen at the same time as the Continentalness checks (unsure why), slowing the search down, unless you make it dependent on one of the above checks.  Spiral iterator out to ±320 blocks from (0,0) Biome search on Spiral Iterator for Lush Cave at Y:128 | [High Lush Cave Islands](https://docs.google.com/document/d/1rCp1kVN46Lxu3yL0TtjPBJ5aTZqb0ycNjB8f9r_jUW0/edit?usp=sharing) |

### Appendix B {#appendix-b}

| Appendix B1 |
| ----- |
|  |
| **Appendix B2** |
|  |

| Appendix C1 |
| ----- |
|   |

### Appendix C

| Appendix C2 |
| ----- |
|  |

| Appendix C3 |
| ----- |
|   |

| Appendix C4 |
| ----- |
|  |

| Appendix C5 |
| ----- |
|  |

| Appendix C6 |
| ----- |
|  |

| Appendix C7 |
| ----- |
|  |

| Appendix C8 |
| ----- |
|  **Seeds per second calculated on an Intel i5-1135G7 processor with 3 threads for the search.**   |
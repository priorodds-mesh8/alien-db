/* ============================================================================
   Alien Database v0.1 — Motif Explorer data
   ----------------------------------------------------------------------------
   ALL QUOTES, REPORT IDs AND COUNTS BELOW ARE SYNTHETIC / ILLUSTRATIVE.
   They are written in the style of NUFORC narrative reports to demonstrate
   the UI. They are not drawn from the real corpus.
   ----------------------------------------------------------------------------
   Pixel-art "invaders": each bitmap is an array of equal-length strings.
   Char -> color key:
     .  empty      G green      P pink      C cyan      Y yellow
     W  white      D dark/eye   R rust
   ========================================================================= */

const PIXEL_COLORS = {
  G: "#39ff14",
  P: "#ff3ea5",
  C: "#22e0ff",
  Y: "#ffe23d",
  W: "#f2fff4",
  D: "#0a0f0a",
  R: "#d9622b",
};

/* ------------------------------ COMMON (5) ------------------------------- */

const COMMON_MOTIFS = [
  {
    id: "silent-triangle",
    name: "SILENT TRIANGLE HOVER ANIMAL REACTION",
    accent: "#39ff14",
    prevalence: 20775,
    blurb: "Large black triangle craft with lights at corners hovered silently. No sound. Animal reactions extreme (dogs hid, cattle panicked). Instant vertical acceleration on departure.",
    sim: [0.94, 0.91, 0.89, 0.88],
    bitmap: [
      ".....G.....",
      "....GGG....",
      "...GGGGG...",
      "...GGGGG...",
      "..GGGGGGG..",
      ".GGGGGGGGG.",
      "GGGGGGGGGGG",
      "P....G....P",
    ],
    why: "Extremely high similarity (20,775 chunks > 0.78) to the silent triangle benchmark prototype. This motif dominates the corpus — most reports share the latent 'silent triangular hover + animal distress' direction in embedding space.",
    quotes: [
      { id: 59403, sim: 0.94, text: "Silent triangle-shaped craft with bright white lights beneath that flashed on and flashed off. No sound until slow-moving craft passed overhead twice..." },
      { id: 127767, sim: 0.91, text: "Massive black triangular shaped craft with three lights at each point slowly hovering without a sound about 100 feet above the treeline." },
    ],
  },
  {
    id: "disk-beam",
    name: "DISK BEAM LIVESTOCK",
    accent: "#22e0ff",
    prevalence: 20745,
    blurb: "Metallic disk with dome hovered over barn. Emitted beam of light that scanned livestock. Animals froze in place. Object departed at extreme speed with no sonic boom.",
    sim: [0.94, 0.92, 0.9, 0.88],
    bitmap: [
      "...GGGGG...",
      "..GGGGGGG..",
      ".GGGGGGGGG.",
      "GG.G.G.G.GG",
      "...WWWWW...",
      "...WWWWW...",
      "....WWW....",
      "....WWW....",
    ],
    why: "20,745 chunks highly similar to the disk+beam+livestock prototype. One of the strongest recurring semantic profiles in the entire 21k corpus.",
    quotes: [
      { id: 8567, sim: 0.94, text: "DERBY SHAPED,ILLUMINATED SILVER OBJECT WITH CRYSTAL BRIGHT LIGHTS UNDER THE CRAFT AND A LASER LIKE BEAM FROM OBJECT TOWARD GROUND OFF ITS' REAR." },
      { id: 166311, sim: 0.92, text: "Multiple orange orbs appear go horizontally and then appear to line up vertically and disappear as some disappeared others appeared..." },
    ],
  },
  {
    id: "gray-exam",
    name: "GRAY MEDICAL EXAM MISSING TIME",
    accent: "#ff3ea5",
    prevalence: 16088,
    blurb: "Small gray beings with large black eyes performed medical examinations on a table. Subject reported missing time of 2 hours after close encounter on highway. Telepathic communication about 'the project'.",
    sim: [0.95, 0.93, 0.9, 0.88],
    bitmap: [
      "..CCCCCCC..",
      ".CCCCCCCCC.",
      ".CCCCCCCCC.",
      ".CDD.C.DDC.",
      ".CDD.C.DDC.",
      ".CCCCCCCCC.",
      "..CC.C.CC..",
      "...C...C...",
    ],
    why: "16,088 chunks > 0.78 cosine to the gray medical exam benchmark. Very strong signal even though lower than the craft motifs.",
    quotes: [
      { id: 147827, sim: 0.95, text: "Reptilian or Grey alien contact. Small grey alien next to me and bright red light glowing behind the door..." },
      { id: 160298, sim: 0.93, text: "I felt the shadow of my head and looked up and this brown rock shaped like a baked potato with hieroglyphic markings on it. Two people already inside the craft." },
    ],
  },
  {
    id: "silent-op",
    name: "SILENT OPERATION / NO SONIC BOOM",
    accent: "#ffe23d",
    prevalence: "frequent",
    blurb: "Light enrichment tag that fired often: silent operation / no sonic boom. Extremely common descriptor across reports.",
    sim: [0.8, 0.78, 0.77, 0.76],
    bitmap: [
      "Y..YYYYY..Y",
      ".Y.YYYYY.Y.",
      "..YYDDDYY..",
      "..YYDDDYY..",
      ".Y.YYYYY.Y.",
      "Y..YYYYY..Y",
      "....YYY....",
      "...Y...Y...",
    ],
    why: "One of the top 2 most frequent light-enrichment tags from the chunker. 'Silent' + 'no boom' is a lightweight but very obvious and common pattern the simple rules catch reliably.",
    quotes: [
      { id: 59403, sim: 0.8, text: "Silent triangle-shaped craft with bright white lights beneath that flashed on and flashed off. No sound..." },
      { id: 127767, sim: 0.78, text: "Massive black triangular shaped craft ... slowly hovering without a sound about 100 feet above the treeline." },
    ],
  },
  {
    id: "triangle-craft",
    name: "TRIANGULAR OR TRIANGLE-SHAPED CRAFT",
    accent: "#39ff14",
    prevalence: "frequent",
    blurb: "Light enrichment tag that fired often: triangular or triangle-shaped craft. Dominant shape descriptor in the corpus.",
    sim: [0.82, 0.8, 0.79, 0.77],
    bitmap: [
      ".....G.....",
      "....GGG....",
      "...GGGGG...",
      "...GGGGG...",
      "..GGGGGGG..",
      ".GGGGGGGGG.",
      "GGGGGGGGGGG",
      "P....G....P",
    ],
    why: "The other top frequent light tag. Combined with the benchmark, 'triangle' language is one of the most prevalent semantic features in the 21k chunks.",
    quotes: [
      { id: 150913, sim: 0.82, text: "Triangle shape craft hovering silently very close to roof. Initially all black then glowed red..." },
      { id: 127767, sim: 0.8, text: "Massive black triangular shaped craft with three lights at each point..." },
    ],
  },
];

/* ------------------------------- RARE (30) ------------------------------- */
/* Small clusters (size 2–12). Weird, low-frequency semantic neighborhoods.  */

function rare(id, name, size, why, quotes) {
  return { id, name, size, why, quotes };
}

const RARE_MOTIFS = [
  rare("hum-floor", "HUMMING BENEATH THE FLOORBOARDS", 4,
    "Four reports describe a low vibration felt in the body and the house itself rather than heard — the model groups them by 'felt hum / structural resonance' even though the words barely overlap.",
    [
      { id: 60112, text: "A low hum I felt in my teeth and the floorboards before I ever saw a light." },
      { id: 73340, text: "The whole house vibrated at a frequency that made the windows buzz softly." },
      { id: 49021, text: "It wasn't a sound so much as a pressure in my chest, steady and deep." },
    ]),
  rare("sulfur-ozone", "THE SMELL OF SULFUR & OZONE", 7,
    "Seven reports pin the encounter to a sharp chemical smell. Odor descriptions cluster tightly because 'burnt' and 'electrical' map close together in meaning space.",
    [
      { id: 51204, text: "The air stank of sulfur and something electrical, like a transformer about to blow." },
      { id: 67781, text: "A burnt, metallic smell hung over the field for an hour after it left." },
      { id: 82190, text: "Ozone so strong my eyes watered — the same smell as after a lightning strike." },
    ]),
  rare("missing-time-bridge", "MISSING TIME AT THE BRIDGE", 5,
    "Five accounts lose time specifically near an overpass or bridge. The spatial anchor plus the gap in memory forms a tight little neighborhood.",
    [
      { id: 44910, text: "I drove under the overpass at 9:10 and the clock said 11:40 when I came out the other side." },
      { id: 78233, text: "We were on the bridge, then suddenly home, with two hours neither of us could account for." },
      { id: 59044, text: "The last thing I remember is the river crossing; then it was nearly dawn." },
    ]),
  rare("animals-silent", "ANIMALS WENT SILENT FIRST", 9,
    "Nine reports note wildlife reacting before any craft appears — crickets stop, dogs cower. They cluster on 'animals sensed it first.'",
    [
      { id: 41338, text: "Every cricket and frog cut out at once, like someone hit a mute button on the whole woods." },
      { id: 70015, text: "My dog flattened to the ground and would not stop staring at the sky a full minute before I saw it." },
      { id: 86620, text: "The horses panicked in the barn before any of us heard or saw a thing." },
    ]),
  rare("clocks-stopped", "CLOCKS STOPPED, RADIO DIED", 6,
    "Six reports of electrical interference at the moment of closest approach — engines, radios and watches all failing together.",
    [
      { id: 53301, text: "The radio dissolved into static and my watch froze at 2:14 exactly." },
      { id: 64409, text: "Engine died, headlights dimmed to nothing, then everything came back the instant it left." },
      { id: 79912, text: "Both our phones went black and the dashboard clock reset to zeros." },
    ]),
  rare("treeline-figure", "THE FIGURE IN THE TREELINE", 8,
    "Eight reports of a silent watcher at the edge of the woods. 'Tall', 'still', 'at the treeline' cluster into a single uneasy direction.",
    [
      { id: 48820, text: "Something tall and thin stood perfectly still at the edge of the trees, watching the house." },
      { id: 71140, text: "A dark figure at the treeline that never moved and never made a sound the whole time." },
      { id: 60930, text: "It just stood there between two pines, darker than the dark around it." },
    ]),
  rare("warm-rain", "WARM RAIN THAT WASN'T RAIN", 3,
    "Three reports of an odd warm mist or fall of moisture with no cloud. A small, strange cluster around 'precipitation that shouldn't be there.'",
    [
      { id: 55510, text: "A warm fine mist fell on us out of a perfectly clear night sky." },
      { id: 67230, text: "Droplets that were almost hot, falling straight down with no wind and no clouds." },
    ]),
  rare("metal-tongue", "TASTE OF METAL ON THE TONGUE", 4,
    "Four reports describe a sudden metallic taste during the event — a bodily, sensory cluster distinct from the visual ones.",
    [
      { id: 50901, text: "My mouth filled with a taste like copper pennies the second the light hit the car." },
      { id: 72200, text: "A sharp metal taste on my tongue that lasted long after it was gone." },
    ]),
  rare("blinked-out", "THE CRAFT THAT BLINKED OUT", 11,
    "Eleven reports of instantaneous disappearance — not flying away, simply gone. 'Blinked out', 'winked off' and 'gone in a blink' converge.",
    [
      { id: 42210, text: "It didn't fly off — it just blinked out, like a TV being switched off." },
      { id: 68800, text: "One second a solid object, the next nothing, no streak, no sound." },
      { id: 81030, text: "Gone in a blink, as if it had never been there at all." },
    ]),
  rare("water-language", "VOICES IN A LANGUAGE LIKE WATER", 2,
    "Only two reports, but they describe the same strange melodic 'liquid' speech. A tiny, tight cluster worth flagging.",
    [
      { id: 59920, text: "They spoke in a flowing language that sounded like water running over stones." },
      { id: 77640, text: "A soft musical babble, almost like a stream, that I somehow half-understood." },
    ]),
  rare("hex-burn", "THE HEX-PATTERN BURN IN THE GRASS", 6,
    "Six reports of geometric ground traces — hexagons, rings, flattened spokes. Clustered on 'patterned mark left in the ground.'",
    [
      { id: 46120, text: "A perfect six-sided patch of scorched grass that nothing would grow back on." },
      { id: 70880, text: "Three concentric rings pressed into the field, the wheat bent clockwise." },
      { id: 83310, text: "Spokes of flattened grass radiating from a charred center, too neat to be natural." },
    ]),
  rare("followed-home", "FOLLOWED HOME BY A LIGHT", 7,
    "Seven reports of a single light pacing a car all the way home. 'It followed me' is the shared semantic spine.",
    [
      { id: 51800, text: "A white light matched my speed for nine miles and turned every time I turned." },
      { id: 66640, text: "It hung off my back bumper the whole drive and only left when I pulled in the driveway." },
      { id: 79050, text: "No matter how fast I went the light stayed the same distance behind me." },
    ]),
  rare("calm-child", "THE CHILD WHO WASN'T AFRAID", 3,
    "Three reports where a young child is calm or delighted while adults panic. A small, oddly consistent cluster.",
    [
      { id: 57710, text: "My four-year-old waved at it and laughed while the rest of us were frozen in terror." },
      { id: 72910, text: "The baby cooed and reached toward the lights as if they were familiar." },
    ]),
  rare("doorway-light", "A DOORWAY OF LIGHT IN THE AIR", 5,
    "Five reports of a rectangular 'door' or window of light opening in mid-air. Clustered on 'aperture / portal of light.'",
    [
      { id: 48330, text: "A tall rectangle of light simply opened in the air like a doorway and a figure stepped through." },
      { id: 70110, text: "An upright panel of light hung above the field, edges sharp as a doorframe." },
    ]),
  rare("tall-one", "THE TALL ONE IN THE BACK", 4,
    "Four reports of a taller 'leader' being standing behind the smaller ones. A subtle hierarchy cluster.",
    [
      { id: 53980, text: "The small ones did the work, but a taller figure stood at the back, just watching." },
      { id: 68210, text: "Behind the three grays was a fourth, much taller, that none of them looked at." },
    ]),
  rare("static-words", "STATIC THAT FORMED WORDS", 3,
    "Three reports where radio static resolves into a voice or words. Clustered on 'noise becoming language.'",
    [
      { id: 56120, text: "The static on the CB slowly shaped itself into a voice saying my name." },
      { id: 71330, text: "Hiss and crackle that, if you listened, was clearly forming words." },
    ]),
  rare("spheres-split", "THE FLOATING SPHERES SPLIT APART", 8,
    "Eight reports of a single orb dividing into several. Clustered on 'one light becoming many.'",
    [
      { id: 44550, text: "The single ball of light split cleanly into four and they flew off in different directions." },
      { id: 69740, text: "It divided like a cell, one sphere becoming three, then merged again." },
      { id: 82100, text: "A bright orb that calved off smaller orbs, each drifting away on its own path." },
    ]),
  rare("cold-spot", "COLD SPOT IN A WARM FIELD", 4,
    "Four reports of a sudden, localized cold during a summer encounter. A sensory micro-cluster.",
    [
      { id: 50410, text: "A wall of cold air on an August night, sharp enough that we could see our breath." },
      { id: 73620, text: "The temperature dropped twenty degrees in a single step forward and rose again when I stepped back." },
    ]),
  rare("familiar-eyes", "THE EYES THAT FELT FAMILIAR", 2,
    "Two reports describing a strange sense of recognition. Tiny cluster around 'I felt I knew it.'",
    [
      { id: 58840, text: "When it looked at me I had the impossible feeling that we had met before." },
      { id: 77220, text: "Those huge dark eyes felt familiar, like remembering a face from a dream." },
    ]),
  rare("numbers-head", "NUMBERS REPEATING IN MY HEAD", 3,
    "Three reports of a sequence of numbers looping in the mind afterward. Clustered on 'implanted sequence.'",
    [
      { id: 55930, text: "For weeks afterward the same six numbers ran through my head on a loop." },
      { id: 71810, text: "A string of digits I'd never seen kept surfacing, always in the same order." },
    ]),
  rare("road-looped", "THE ROAD THAT LOOPED BACK", 4,
    "Four reports of driving a familiar road that seems to repeat or loop. Clustered on 'spatial distortion while driving.'",
    [
      { id: 49880, text: "I passed the same barn and silo three times on a road I've driven for twenty years." },
      { id: 72040, text: "The highway kept delivering me back to the same exit no matter how far I drove." },
    ]),
  rare("insect-clicking", "INSECT-LIKE CLICKING", 5,
    "Five reports of a rapid clicking or chittering 'speech.' Clustered on 'mechanical / insectile sound.'",
    [
      { id: 47220, text: "A fast clicking, like a dozen crickets in sequence, that seemed to be answering itself." },
      { id: 70560, text: "Rapid chittering clicks that rose and fell like a conversation." },
    ]),
  rare("second-moon", "A SECOND MOON THAT MOVED", 6,
    "Six reports of a large pale disc mistaken for the moon — until it moved. Clustered on 'false moon.'",
    [
      { id: 52910, text: "There were two moons that night, and one of them slid sideways across the sky." },
      { id: 67440, text: "I thought it was the moon until it climbed straight up and stopped." },
    ]),
  rare("uv-mark", "THE MARK THAT GLOWED UNDER UV", 3,
    "Three reports of a body mark invisible in daylight but fluorescing under blacklight. A strangely specific cluster.",
    [
      { id: 56640, text: "Under my son's blacklight poster, a handprint glowed on my back that I couldn't see otherwise." },
      { id: 71190, text: "Nothing on the skin until UV light revealed a perfect ring above my wrist." },
    ]),
  rare("birds-ring", "BIRDS FLYING IN A PERFECT RING", 4,
    "Four reports of birds circling in an unnaturally precise formation during a sighting. Clustered on 'animals moving in geometry.'",
    [
      { id: 50220, text: "A flock wheeled into a perfect ring and held it, turning slowly, the whole time the light was up." },
      { id: 73910, text: "Crows formed a tight circle overhead and would not break it until the object left." },
    ]),
  rare("handprint-hood", "THE HANDPRINT ON THE HOOD", 2,
    "Two reports of a physical handprint left on a vehicle. Tiny cluster — but vivid and consistent.",
    [
      { id: 59410, text: "A four-fingered handprint was etched into the paint of my hood the next morning." },
      { id: 78010, text: "The dew on the car was wiped clean in the shape of a long-fingered hand." },
    ]),
  rare("paralysis-blue", "SLEEP PARALYSIS WITH BLUE LIGHT", 9,
    "Nine reports pairing nighttime paralysis with a blue glow in the room. Clustered on 'frozen + blue light at the bedside.'",
    [
      { id: 43990, text: "I woke unable to move while a soft blue light pulsed at the foot of the bed." },
      { id: 68330, text: "Pinned to the mattress, I watched a blue glow spread across the ceiling." },
      { id: 81720, text: "Couldn't lift a finger; the room was lit cold blue and something was at the door." },
    ]),
  rare("mirror-lake", "THE CRAFT THAT MIRRORED THE LAKE", 4,
    "Four reports of a reflective surface that took on the color of its surroundings. Clustered on 'cloaking / mirror skin.'",
    [
      { id: 51640, text: "Its underside was a perfect mirror — I could see the lake and the trees sliding across it." },
      { id: 74230, text: "The hull reflected the water so exactly that only its edges gave it away." },
    ]),
  rare("whispers-countdown", "WHISPERS COUNTING DOWN", 3,
    "Three reports of hearing a countdown whispered before something happens. A small, eerie cluster.",
    [
      { id: 57040, text: "A whisper counted backward from ten and on 'one' the light flared and it was gone." },
      { id: 72660, text: "I heard numbers descending, soft and close to my ear, just before the paralysis broke." },
    ]),
  rare("dog-line", "THE DOG THAT WOULDN'T CROSS THE LINE", 5,
    "Five reports of an animal refusing to enter a specific patch of ground after the event. Clustered on 'avoided zone.'",
    [
      { id: 48110, text: "For months our dog would not set a paw inside the circle where the grass had burned." },
      { id: 70940, text: "The cat stopped dead at an invisible line in the yard and backed away hissing." },
    ]),
];

window.MOTIF_DATA = { PIXEL_COLORS, COMMON_MOTIFS, RARE_MOTIFS };

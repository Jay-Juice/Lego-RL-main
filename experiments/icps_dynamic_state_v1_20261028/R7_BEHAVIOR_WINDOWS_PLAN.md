# Explicit issue anchors and bounded AST relations

Predeclared development experiment:607previously seen inputs,366exactmapped
targets/77repositories, fixed saved passage24 candidates. No private case-score
inspection or R6confirmation use. Original256baseline205/134;384baseline213/174.

Six arms: original diverse6, bounded structural reweighting of original seeds,
and reweighting plus source-derived seed additions; each at256/384actualQwen
tokens. Same original token-aware allocator, diversity, max3 nonoverlap windows,
full source lines and context expansion. Frozen runtime192/128/4096 untouched.

Signals are issue-explicit code identifiers/calls/named entities/traceback frame
names, exact literal error messages in current AST calls/raises, a weak named
entity prior, and one-hop unique-name direct/self/cls callee prior. Seed-related
nearest preceding local stores, enclosing if guards and later returns receive
bounded evidence. Nested lexical scopes excluded. These are static syntactic
relations, not sound runtime resolution, alias analysis or semantic dataflow.
No exception trace coordinates, tests, execution, patch labels or future state
are used to manufacture PI. Quoted issue examples are ordinary issue input.

Fixed prior .5explicit/.35callee; direct call/literal1.5; store.75,guard1,return.5.
Window bonus=min(2,prior+max(line_cue)+mean(line_cue)); adjusted original score
=score*(1+.35*bonus)+.5*bonus. No normalized rank compression. Extra seeds only
at top6structural anchors/entity, same3/5/7line windows, original lexical score.
All original proposals retained. Unsignaled tasks exactly preserve baseline.

Generator asserts607exact prior passage24_256 payload replay, actualQwen
roundtrip/cap/source/nonoverlap/max3. Landlock per-file input grants deny9label
and prior-score paths. Freeze all607x6outputs before scoring. Report candidate,
any-target, full-any AND full-all, density, token cost and paired repo intervals.
Intervals exploratory and unadjusted after adaptive development. No100%claim,
independent admission, semantic benefit or formal training from this experiment.

Windows D:/ai project/RL学习/Lego-RL-main source authority; WSL rsync preview,
review/sync/SHA to SSH A800:/media/ubuntu/D1/zsj/Lego-RL-main. Unique source/queue
behavior_windows_r7; only aggregate/freeze reports downloaded; all private state
and failed prior experiments preserved.

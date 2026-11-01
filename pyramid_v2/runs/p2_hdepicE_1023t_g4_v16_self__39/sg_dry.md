# sg dry-run p2_hdepicE_1023t_g4_v16_self__39

goal: Rinse the chickpeas, then place the chickpeas on a towel and lightly towel dry them so they aren't wet from rinsing. You can remove any loose skins at this time too.

## sub-goal 1 [29.9-62.8, 33s] Open the can of chickpeas.
- s1e1 (action) The person opens the can of chickpeas using a pull tab or can opener. | objects ['can', 'chickpeas', 'can opener'] | skills ['object_recognition', 'action_recognition', 'event_object_role'] | time [55.64, 62.84] (1 narration(s), best score 5.5)
- s1e2 (sound) A popping or cracking sound is heard as the can seal is broken. | objects ['can'] | skills ['sound_action_binding'] | time [29.88, 31.07] (1 narration(s), best score 2.0)

## sub-goal 2 [70.5-89.3, 19s] Drain the chickpeas and rinse the can.
- s2e1 (action) The person tips the can to pour the aquafaba liquid down the sink drain. | objects ['can', 'liquid', 'sink'] | skills ['action_recognition', 'object_state_change'] | time [76.26, 77.85] (1 narration(s), best score 4.5)
- s2e2 (action) The person runs tap water into the can to rinse the remaining liquid. | objects ['can', 'water', 'faucet'] | skills ['action_recognition', 'event_object_role'] | time [79.37, 81.14] (1 narration(s), best score 7.0)
- s2e3 (sound) The sound of running water splashing into the metal can. | objects ['water', 'can'] | skills ['sound_action_binding'] | time [73.231, 90.27] (1 narration(s), best score 6.0)

## sub-goal 3 [89.1-128.2, 39s] Rinse and drain the chickpeas in the colander.
- s3e1 (action) The person pours the chickpeas from the can into a colander. | objects ['chickpeas', 'can', 'colander'] | skills ['action_recognition', 'object_state_change'] | time [89.11, 100.7] (3 narration(s), best score 4.0)
- s3e2 (action) The person runs water over the chickpeas in the colander. | objects ['chickpeas', 'water', 'colander'] | skills ['action_recognition', 'event_object_role'] | time [89.11, 90.49] (1 narration(s), best score 9.5)
- s3e3 (action) The person shakes the colander up and down to drain the excess water. | objects ['colander', 'chickpeas'] | skills ['action_recognition'] | time [89.11, 100.7] (3 narration(s), best score 4.5)

## sub-goal 4 [129.0-153.1, 24s] Transfer the chickpeas to paper towels and dry them.
- s4e1 (action) The person dumps the rinsed chickpeas from the colander onto paper towels. | objects ['chickpeas', 'colander', 'paper towels'] | skills ['action_recognition', 'object_state_change'] | time [137.25, 142.75] (2 narration(s), best score 6.0)
- s4e2 (action) The person gently rubs or pats the chickpeas with another paper towel. | objects ['chickpeas', 'paper towels'] | skills ['action_recognition', 'event_object_role'] | time [137.25, 145.02] (4 narration(s), best score 4.5)

## sub-goal 5 [156.4-182.7, 26s] Remove loose skins from the chickpeas.
- s5e1 (action) The person pinches individual chickpeas to slide off their translucent skins. | objects ['chickpeas', 'skins', 'fingers'] | skills ['action_recognition', 'event_object_role'] | time [156.36, 159.5] (1 narration(s), best score 7.5)
- s5e2 (placement) The person discards the removed skins into a pile or a waste bin. | objects ['skins', 'bin'] | skills ['object_location_at_time'] | time [165.33, 176.43] (8 narration(s), best score 2.5)

## sub-goal 6 [185.4-226.0, 41s] Transfer the chickpeas to a baking tray and continue removing loose skins.
- s6e1 (action) The person moves the dried chickpeas from the paper towels onto a baking tray. | objects ['chickpeas', 'paper towels', 'baking tray'] | skills ['action_recognition', 'object_state_change'] | time [189.0, 200.11] (4 narration(s), best score 8.0)
- s6e2 (action) The person picks off any remaining loose skins from the chickpeas now on the tray. | objects ['chickpeas', 'skins', 'baking tray'] | skills ['action_recognition'] | time [197.89, 200.11] (1 narration(s), best score 10.0)

## relations (L3)
- r1 causal_prerequisite -> causal_prerequisite_reasoning: ['s1e1', 's2e1'] | ask: Why was the person able to pour liquid out of the can? | hint: The can was opened in the previous step.
- r2 object_continuity -> cross_event_integration: ['s2e2', 's3e1'] | ask: What is being poured into the colander? | hint: The chickpeas that were just rinsed inside the can.
- r3 object_continuity -> cross_event_integration: ['s3e3', 's4e1'] | ask: Where did the chickpeas on the paper towels come from? | hint: They were transferred from the colander after being shaken dry.
- r4 state_change -> cross_event_integration: ['s4e2', 's5e1'] | ask: What is the moisture state of the chickpeas being peeled? | hint: They were just patted dry with paper towels.
- r5 object_continuity -> cross_event_integration: ['s5e1', 's6e1'] | ask: What is being transferred to the baking tray? | hint: The chickpeas that just had their loose skins removed.
- d1 object_continuity -> cross_event_integration: ['s3e2', 's4e1'] | ask: what happened to the shared object (chickpea, colander) between the earlier event and the later one; what the later event shows that the earlier did not | hint: The person runs water over the chickpeas in the colander. -> The person dumps the rinsed chickpeas from the colander onto paper towels.
- d2 object_continuity -> cross_event_integration: ['s3e1', 's4e1'] | ask: what happened to the shared object (chickpea, colander) between the earlier event and the later one; what the later event shows that the earlier did not | hint: The person pours the chickpeas from the can into a colander. -> The person dumps the rinsed chickpeas from the colander onto paper towels.
- d3 object_continuity -> cross_event_integration: ['s5e1', 's6e2'] | ask: what happened to the shared object (chickpea, skin) between the earlier event and the later one; what the later event shows that the earlier did not | hint: The person pinches individual chickpeas to slide off their translucent skins. -> The person picks off any remaining loose skins from the chickpeas now on the tray.
- d4 object_continuity -> cross_event_integration: ['s1e2', 's2e1'] | ask: what happened to the shared object (can) between the earlier event and the later one; what the later event shows that the earlier did not | hint: A popping or cracking sound is heard as the can seal is broken. -> The person tips the can to pour the aquafaba liquid down the sink drain.
- d5 object_continuity -> cross_event_integration: ['s1e2', 's2e2'] | ask: what happened to the shared object (can) between the earlier event and the later one; what the later event shows that the earlier did not | hint: A popping or cracking sound is heard as the can seal is broken. -> The person runs tap water into the can to rinse the remaining liquid.
- d6 object_continuity -> cross_event_integration: ['s1e2', 's2e3'] | ask: what happened to the shared object (can) between the earlier event and the later one; what the later event shows that the earlier did not | hint: A popping or cracking sound is heard as the can seal is broken. -> The sound of running water splashing into the metal can.
- d7 object_continuity -> cross_event_integration: ['s1e1', 's2e2'] | ask: what happened to the shared object (can) between the earlier event and the later one; what the later event shows that the earlier did not | hint: The person opens the can of chickpeas using a pull tab or can opener. -> The person runs tap water into the can to rinse the remaining liquid.
- d8 object_continuity -> cross_event_integration: ['s1e1', 's2e3'] | ask: what happened to the shared object (can) between the earlier event and the later one; what the later event shows that the earlier did not | hint: The person opens the can of chickpeas using a pull tab or can opener. -> The sound of running water splashing into the metal can.

## decision points (L4)
- idx 2 real=True: Deciding to drain the liquid directly from the can before fully emptying the chickpeas is a distinct procedural choice.
- idx 3 real=True: Moving from rinsing inside the can to using a colander for a more thorough rinse requires fetching a new tool and changing the action.
- idx 4 real=True: Transitioning from washing to drying requires setting up paper towels and changing the physical interaction with the chickpeas.
- idx 5 real=True: Moving from bulk drying to the meticulous, individual task of peeling skins is a major shift in action and focus.
- idx 6 real=True: Deciding to transfer the chickpeas to a baking tray to finish the peeling process involves a spatial relocation and preparing for the next recipe stage.
- idx 7 real=True: The task is complete; deciding to stop peeling skins and move on to the next recipe step (like seasoning or roasting) is a real decision.

## L1 pools
### spatial_near: 1 clusters
- sg1 win [29.88, 62.84] events ['s1e1', 's1e2'] anchors 1 core 21 bands {1:0, 2:1, 3:0, 4:0} knob ['margin_m_neg']
### spatial_side: 0 clusters (NOT_EVALUATED: no expected-event cluster for this skill on this task (sg mode))
### object_recognition: 6 clusters
- sg1 win [29.88, 62.84] events ['s1e1', 's1e2'] anchors 7 core 9 bands {1:5, 2:1, 3:0, 4:1} knob ['n_other_narrations']
- sg2 win [70.48, 89.27] events ['s2e1', 's2e2', 's2e3'] anchors 15 core 18 bands {1:0, 2:5, 3:4, 4:6} knob ['n_other_narrations']
- sg3 win [89.11, 128.18] events ['s3e1', 's3e2', 's3e3'] anchors 10 core 12 bands {1:7, 2:2, 3:1, 4:0} knob ['n_other_narrations']
- sg4 win [129.04, 153.1] events ['s4e1', 's4e2'] anchors 13 core 14 bands {1:5, 2:4, 3:2, 4:2} knob ['n_other_narrations']
- sg5 win [156.36, 182.73] events ['s5e1', 's5e2'] anchors 19 core 21 bands {1:0, 2:3, 3:9, 4:7} knob ['n_other_narrations']
- sg6 win [185.36, 225.97] events ['s6e1', 's6e2'] anchors 12 core 14 bands {1:2, 2:4, 3:4, 4:2} knob ['n_other_narrations']
### object_location_at_time: 3 clusters
- sg1 win [29.88, 62.84] events ['s1e1', 's1e2'] anchors 1 core 7 bands {1:0, 2:0, 3:0, 4:1} knob ['area_neg']
- sg2 win [70.48, 89.27] events ['s2e1', 's2e2', 's2e3'] anchors 2 core 10 bands {1:0, 2:1, 3:1, 4:0} knob ['area_neg']
- sg4 win [129.04, 153.1] events ['s4e1', 's4e2'] anchors 1 core 8 bands {1:1, 2:0, 3:0, 4:0} knob ['area_neg']
### object_grounding: 5 clusters
- sg1 win [29.933, 30.933] events ['s1e1', 's1e2'] anchors 1 core 7 bands {1:0, 2:0, 3:1, 4:0} knob ['area_neg']
- sg1 win [37.2, 38.2] events ['s1e1', 's1e2'] anchors 1 core 6 bands {1:0, 2:0, 3:0, 4:1} knob ['area_neg']
- sg2 win [72.667, 73.667] events ['s2e1', 's2e2', 's2e3'] anchors 1 core 13 bands {1:1, 2:0, 3:0, 4:0} knob ['area_neg']
- sg2 win [89.133, 90.133] events ['s2e1', 's2e2', 's2e3'] anchors 1 core 10 bands {1:1, 2:0, 3:0, 4:0} knob ['area_neg']
- sg4 win [134.667, 135.667] events ['s4e1', 's4e2'] anchors 1 core 10 bands {1:0, 2:1, 3:0, 4:0} knob ['area_neg']

## L2 pools
### sound_action_binding: 5 clusters
- sg1 win [29.88, 62.84] events ['s1e1', 's1e2'] anchors 11 core 22 tiers {1: 15.0, 2: 30.0, 3: 32.96, 4: 32.96}
- sg2 win [70.48, 89.27] events ['s2e1', 's2e2', 's2e3'] anchors 5 core 26 tiers {1: 15.0, 2: 30.0, 3: 18.79, 4: 18.79}
- sg3 win [89.11, 128.18] events ['s3e1', 's3e2', 's3e3'] anchors 4 core 16 tiers {1: 15.0, 2: 30.0, 3: 39.07, 4: 39.07}
- sg4 win [129.04, 153.1] events ['s4e1', 's4e2'] anchors 4 core 21 tiers {1: 15.0, 2: 30.0, 3: 24.06, 4: 24.06}
- sg6 win [185.36, 225.97] events ['s6e1', 's6e2'] anchors 4 core 18 tiers {1: 15.0, 2: 30.0, 3: 40.61, 4: 40.61}
### object_state_change: 3 clusters
- sg1 win [29.88, 62.84] events ['s1e1', 's1e2'] anchors 1 core 9 tiers {1: 15.0, 2: 30.0, 3: 32.96, 4: 32.96}
- sg2 win [70.48, 89.27] events ['s2e1', 's2e2', 's2e3'] anchors 2 core 18 tiers {1: 15.0, 2: 30.0, 3: 18.79, 4: 18.79}
- sg4 win [129.04, 153.1] events ['s4e1', 's4e2'] anchors 1 core 15 tiers {1: 15.0, 2: 30.0, 3: 24.06, 4: 24.06}
### action_temporal_order: 6 clusters
- sg1 win [29.88, 62.84] events ['s1e1', 's1e2'] anchors 7 core 8 tiers {1: 15.0, 2: 30.0, 3: 32.96, 4: 32.96}
- sg2 win [70.48, 89.27] events ['s2e1', 's2e2', 's2e3'] anchors 15 core 16 tiers {1: 15.0, 2: 30.0, 3: 18.79, 4: 18.79}
- sg3 win [89.11, 128.18] events ['s3e1', 's3e2', 's3e3'] anchors 10 core 11 tiers {1: 15.0, 2: 30.0, 3: 39.07, 4: 39.07}
- sg4 win [129.04, 153.1] events ['s4e1', 's4e2'] anchors 13 core 14 tiers {1: 15.0, 2: 30.0, 3: 24.06, 4: 24.06}
- sg5 win [156.36, 182.73] events ['s5e1', 's5e2'] anchors 19 core 20 tiers {1: 15.0, 2: 30.0, 3: 26.37, 4: 26.37}
- sg6 win [185.36, 225.97] events ['s6e1', 's6e2'] anchors 12 core 13 tiers {1: 15.0, 2: 30.0, 3: 40.61, 4: 40.61}
### action_recognition: 6 clusters
- sg1 win [29.88, 62.84] events ['s1e1', 's1e2'] anchors 7 core 11 tiers {1: 15.0, 2: 30.0, 3: 32.96, 4: 32.96}
- sg2 win [70.48, 89.27] events ['s2e1', 's2e2', 's2e3'] anchors 15 core 21 tiers {1: 15.0, 2: 30.0, 3: 18.79, 4: 18.79}
- sg3 win [89.11, 128.18] events ['s3e1', 's3e2', 's3e3'] anchors 10 core 12 tiers {1: 15.0, 2: 30.0, 3: 39.07, 4: 39.07}
- sg4 win [129.04, 153.1] events ['s4e1', 's4e2'] anchors 13 core 17 tiers {1: 15.0, 2: 30.0, 3: 24.06, 4: 24.06}
- sg5 win [156.36, 182.73] events ['s5e1', 's5e2'] anchors 19 core 20 tiers {1: 15.0, 2: 30.0, 3: 26.37, 4: 26.37}
- sg6 win [185.36, 225.97] events ['s6e1', 's6e2'] anchors 12 core 14 tiers {1: 15.0, 2: 30.0, 3: 40.61, 4: 40.61}
### event_object_role: 6 clusters
- sg1 win [29.88, 62.84] events ['s1e1', 's1e2'] anchors 3 core 11 tiers {1: 15.0, 2: 30.0, 3: 32.96, 4: 32.96}
- sg2 win [70.48, 89.27] events ['s2e1', 's2e2', 's2e3'] anchors 13 core 21 tiers {1: 15.0, 2: 30.0, 3: 18.79, 4: 18.79}
- sg3 win [89.11, 128.18] events ['s3e1', 's3e2', 's3e3'] anchors 9 core 12 tiers {1: 15.0, 2: 30.0, 3: 39.07, 4: 39.07}
- sg4 win [129.04, 153.1] events ['s4e1', 's4e2'] anchors 9 core 17 tiers {1: 15.0, 2: 30.0, 3: 24.06, 4: 24.06}
- sg5 win [156.36, 182.73] events ['s5e1', 's5e2'] anchors 18 core 20 tiers {1: 15.0, 2: 30.0, 3: 26.37, 4: 26.37}
- sg6 win [185.36, 225.97] events ['s6e1', 's6e2'] anchors 11 core 14 tiers {1: 15.0, 2: 30.0, 3: 40.61, 4: 40.61}
### sound_anchored_spatial_near: 2 clusters
- sg1 win [29.88, 62.84] events ['s1e1', 's1e2'] anchors 3 core 31 tiers {1: 15.0, 2: 30.0, 3: 32.96, 4: 32.96}
- sg2 win [70.48, 89.27] events ['s2e1', 's2e2', 's2e3'] anchors 2 core 10 tiers {1: 15.0, 2: 30.0, 3: 18.79, 4: 18.79}
### sound_anchored_spatial_side: 0 clusters (NOT_EVALUATED: no expected-event cluster for this skill on this task (sg mode))
### sound_movement_binding: 3 clusters
- sg1 win [29.88, 62.84] events ['s1e1', 's1e2'] anchors 11 core 14 tiers {1: 15.0, 2: 30.0, 3: 32.96, 4: 32.96}
- sg2 win [70.48, 89.27] events ['s2e1', 's2e2', 's2e3'] anchors 5 core 9 tiers {1: 15.0, 2: 30.0, 3: 18.79, 4: 18.79}
- sg4 win [129.04, 153.1] events ['s4e1', 's4e2'] anchors 4 core 7 tiers {1: 15.0, 2: 30.0, 3: 24.06, 4: 24.06}

## L3 pools
### cross_event_integration: 48 clusters
- r2 (planner) tier 1 sub-goals [2, 3] win [70.48, 128.18] (57.7s, sub-goal k and k+1 only) in-clip [2, 3] core 24
- r2 (planner) tier 2 sub-goals [2, 3] win [29.88, 153.1] (123.2s, previous + the pair + next sub-goal) in-clip [1, 2, 3, 4] core 26
- r2 (planner) tier 3 sub-goals [2, 3] win [9.33, 189.33] (180.0s, 180 s centred on the pair, single choice) in-clip [1, 2, 3, 4, 5, 6] core 28
- r2 (planner) tier 4 sub-goals [2, 3] win [9.33, 189.33] (180.0s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4, 5, 6] core 28
- r3 (planner) tier 1 sub-goals [3, 4] win [89.11, 153.1] (64.0s, sub-goal k and k+1 only) in-clip [2, 3, 4] core 24
- r3 (planner) tier 2 sub-goals [3, 4] win [70.48, 182.73] (112.2s, previous + the pair + next sub-goal) in-clip [2, 3, 4, 5] core 27
- r3 (planner) tier 3 sub-goals [3, 4] win [31.105, 211.105] (180.0s, 180 s centred on the pair, single choice) in-clip [1, 2, 3, 4, 5, 6] core 29
- r3 (planner) tier 4 sub-goals [3, 4] win [31.105, 211.105] (180.0s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4, 5, 6] core 29
- r4 (planner) tier 1 sub-goals [4, 5] win [129.04, 182.73] (53.7s, sub-goal k and k+1 only) in-clip [4, 5] core 22
- r4 (planner) tier 2 sub-goals [4, 5] win [89.11, 225.97] (136.9s, previous + the pair + next sub-goal) in-clip [2, 3, 4, 5, 6] core 25
- r4 (planner) tier 3 sub-goals [4, 5] win [65.885, 245.885] (180.0s, 180 s centred on the pair, single choice) in-clip [2, 3, 4, 5, 6] core 25
- r4 (planner) tier 4 sub-goals [4, 5] win [65.885, 245.885] (180.0s, 180 s centred on the pair, short answer) in-clip [2, 3, 4, 5, 6] core 25
- r5 (planner) tier 1 sub-goals [5, 6] win [156.36, 225.97] (69.6s, sub-goal k and k+1 only) in-clip [5, 6] core 24
- r5 (planner) tier 2 sub-goals [5, 6] win [129.04, 225.97] (96.9s, previous + the pair + next sub-goal) in-clip [4, 5, 6] core 26
- r5 (planner) tier 3 sub-goals [5, 6] win [101.165, 281.165] (180.0s, 180 s centred on the pair, single choice) in-clip [3, 4, 5, 6] core 27
- r5 (planner) tier 4 sub-goals [5, 6] win [101.165, 281.165] (180.0s, 180 s centred on the pair, short answer) in-clip [3, 4, 5, 6] core 27
- d1 (derived) tier 1 sub-goals [3, 4] win [89.11, 153.1] (64.0s, sub-goal k and k+1 only) in-clip [2, 3, 4] core 21
- d1 (derived) tier 2 sub-goals [3, 4] win [70.48, 182.73] (112.2s, previous + the pair + next sub-goal) in-clip [2, 3, 4, 5] core 24
- d1 (derived) tier 3 sub-goals [3, 4] win [31.105, 211.105] (180.0s, 180 s centred on the pair, single choice) in-clip [1, 2, 3, 4, 5, 6] core 26
- d1 (derived) tier 4 sub-goals [3, 4] win [31.105, 211.105] (180.0s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4, 5, 6] core 26
- d2 (derived) tier 1 sub-goals [3, 4] win [89.11, 153.1] (64.0s, sub-goal k and k+1 only) in-clip [2, 3, 4] core 24
- d2 (derived) tier 2 sub-goals [3, 4] win [70.48, 182.73] (112.2s, previous + the pair + next sub-goal) in-clip [2, 3, 4, 5] core 27
- d2 (derived) tier 3 sub-goals [3, 4] win [31.105, 211.105] (180.0s, 180 s centred on the pair, single choice) in-clip [1, 2, 3, 4, 5, 6] core 29
- d2 (derived) tier 4 sub-goals [3, 4] win [31.105, 211.105] (180.0s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4, 5, 6] core 29
- d3 (derived) tier 1 sub-goals [5, 6] win [156.36, 225.97] (69.6s, sub-goal k and k+1 only) in-clip [5, 6] core 16
- d3 (derived) tier 2 sub-goals [5, 6] win [129.04, 225.97] (96.9s, previous + the pair + next sub-goal) in-clip [4, 5, 6] core 18
- d3 (derived) tier 3 sub-goals [5, 6] win [101.165, 281.165] (180.0s, 180 s centred on the pair, single choice) in-clip [3, 4, 5, 6] core 19
- d3 (derived) tier 4 sub-goals [5, 6] win [101.165, 281.165] (180.0s, 180 s centred on the pair, short answer) in-clip [3, 4, 5, 6] core 19
- d4 (derived) tier 1 sub-goals [1, 2] win [29.88, 89.27] (59.4s, sub-goal k and k+1 only) in-clip [1, 2, 3] core 41
- d4 (derived) tier 2 sub-goals [1, 2] win [29.88, 128.18] (98.3s, previous + the pair + next sub-goal) in-clip [1, 2, 3] core 41
- d4 (derived) tier 3 sub-goals [1, 2] win [0.0, 149.575] (149.6s, 180 s centred on the pair, single choice) in-clip [1, 2, 3, 4] core 53
- d4 (derived) tier 4 sub-goals [1, 2] win [0.0, 149.575] (149.6s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4] core 53
- d5 (derived) tier 1 sub-goals [1, 2] win [29.88, 89.27] (59.4s, sub-goal k and k+1 only) in-clip [1, 2, 3] core 37
- d5 (derived) tier 2 sub-goals [1, 2] win [29.88, 128.18] (98.3s, previous + the pair + next sub-goal) in-clip [1, 2, 3] core 37
- d5 (derived) tier 3 sub-goals [1, 2] win [0.0, 149.575] (149.6s, 180 s centred on the pair, single choice) in-clip [1, 2, 3, 4] core 49
- d5 (derived) tier 4 sub-goals [1, 2] win [0.0, 149.575] (149.6s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4] core 49
- d6 (derived) tier 1 sub-goals [1, 2] win [29.88, 89.27] (59.4s, sub-goal k and k+1 only) in-clip [1, 2, 3] core 54
- d6 (derived) tier 2 sub-goals [1, 2] win [29.88, 128.18] (98.3s, previous + the pair + next sub-goal) in-clip [1, 2, 3] core 56
- d6 (derived) tier 3 sub-goals [1, 2] win [0.0, 149.575] (149.6s, 180 s centred on the pair, single choice) in-clip [1, 2, 3, 4] core 68
- d6 (derived) tier 4 sub-goals [1, 2] win [0.0, 149.575] (149.6s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4] core 68
- d7 (derived) tier 1 sub-goals [1, 2] win [29.88, 89.27] (59.4s, sub-goal k and k+1 only) in-clip [1, 2, 3] core 35
- d7 (derived) tier 2 sub-goals [1, 2] win [29.88, 128.18] (98.3s, previous + the pair + next sub-goal) in-clip [1, 2, 3] core 35
- d7 (derived) tier 3 sub-goals [1, 2] win [0.0, 149.575] (149.6s, 180 s centred on the pair, single choice) in-clip [1, 2, 3, 4] core 36
- d7 (derived) tier 4 sub-goals [1, 2] win [0.0, 149.575] (149.6s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4] core 36
- d8 (derived) tier 1 sub-goals [1, 2] win [29.88, 89.27] (59.4s, sub-goal k and k+1 only) in-clip [1, 2, 3] core 52
- d8 (derived) tier 2 sub-goals [1, 2] win [29.88, 128.18] (98.3s, previous + the pair + next sub-goal) in-clip [1, 2, 3] core 54
- d8 (derived) tier 3 sub-goals [1, 2] win [0.0, 149.575] (149.6s, 180 s centred on the pair, single choice) in-clip [1, 2, 3, 4] core 55
- d8 (derived) tier 4 sub-goals [1, 2] win [0.0, 149.575] (149.6s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4] core 55
### hidden_state_inference: 0 clusters (NOT_EVALUATED: no expected-event cluster for this skill on this task (sg mode))
### spatial_state_integration: 0 clusters (NOT_EVALUATED: no expected-event cluster for this skill on this task (sg mode))
### causal_prerequisite_reasoning: 4 clusters
- r1 (planner) tier 1 sub-goals [1, 2] win [29.88, 89.27] (59.4s, sub-goal k and k+1 only) in-clip [1, 2, 3] core 39
- r1 (planner) tier 2 sub-goals [1, 2] win [29.88, 128.18] (98.3s, previous + the pair + next sub-goal) in-clip [1, 2, 3] core 39
- r1 (planner) tier 3 sub-goals [1, 2] win [0.0, 149.575] (149.6s, 180 s centred on the pair, single choice) in-clip [1, 2, 3, 4] core 40
- r1 (planner) tier 4 sub-goals [1, 2] win [0.0, 149.575] (149.6s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4] core 40

## L4 pools
### goal_conditioned_planning: 6 clusters
- decision idx 2 win [29.88, 70.48] cutoff 70.48 remaining 5 final=False core 25
- decision idx 3 win [70.48, 89.11] cutoff 89.11 remaining 4 final=False core 20
- decision idx 4 win [89.11, 129.04] cutoff 129.04 remaining 3 final=False core 30
- decision idx 5 win [129.04, 156.36] cutoff 156.36 remaining 2 final=False core 22
- decision idx 6 win [156.36, 185.36] cutoff 185.36 remaining 1 final=False core 27
- decision idx 7 win [185.36, 225.97] cutoff 225.97 remaining 0 final=True core 32

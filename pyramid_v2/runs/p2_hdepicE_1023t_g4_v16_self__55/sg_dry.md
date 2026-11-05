# sg dry-run p2_hdepicE_1023t_g4_v16_self__55

goal: Dredge each Chicken-cheese ball into flour, then dip into egg and roll in the breadcrumbs, ensuring the entire surface of the chicken ball is covered in breadcrumbs.

## sub-goal 1 [6.3-30.1, 24s] Set up the breadcrumbs in a bowl
- s1e1 (action) Pour breadcrumbs from the container into a bowl. | objects ['breadcrumbs', 'container', 'bowl'] | skills ['object_recognition', 'action_recognition', 'event_object_role'] | time [28.32, 30.05] (1 narration(s), best score 5.5)
- s1e2 (sound) The rustling sound of breadcrumbs hitting the bowl. | objects ['breadcrumbs', 'bowl'] | skills ['sound_action_binding', 'sound_movement_binding'] | time [28.32, 30.05] (1 narration(s), best score 5.5)

## sub-goal 2 [30.1-40.8, 11s] Store the breadcrumbs container and prepare the flour bowl
- s2e1 (placement) Place the breadcrumbs container away in a storage area. | objects ['container', 'cabinet'] | skills ['object_location_at_time', 'object_state_change'] | time [29.15, 40.78] (2 narration(s), best score 4.0)
- s2e2 (placement) Place an empty bowl on the counter for the flour. | objects ['bowl', 'counter'] | skills ['object_location_at_time', 'spatial_near'] | time [30.309, 36.67] (1 narration(s), best score 6.0)

## sub-goal 3 [40.9-53.9, 13s] Retrieve flour from the cabinet and pour it into the bowl
- s3e1 (action) Take the flour from the cabinet. | objects ['flour', 'cabinet'] | skills ['object_recognition', 'object_state_change'] | time [40.91, 48.99] (6 narration(s), best score 4.0)
- s3e2 (action) Pour the flour into the empty bowl. | objects ['flour', 'bowl'] | skills ['action_recognition', 'event_object_role'] | time [46.54, 51.71] (3 narration(s), best score 5.5)

## sub-goal 4 [74.0-130.4, 56s] Form the first chicken ball and coat it with flour
- s4e1 (action) Shape the chicken and cheese mixture into a ball using hands. | objects ['chicken', 'cheese', 'hands'] | skills ['action_recognition', 'object_recognition'] | time [74.02, 81.23] (2 narration(s), best score 4.0)
- s4e2 (action) Roll the chicken ball in the flour bowl to coat it. | objects ['chicken ball', 'flour', 'bowl'] | skills ['action_recognition', 'event_object_role'] | time [78.16, 87.63] (6 narration(s), best score 9.5)

## sub-goal 5 [130.8-149.8, 19s] Dip the first chicken ball in egg and coat it with breadcrumbs
- s5e1 (action) Dip the floured chicken ball into the egg bowl. | objects ['chicken ball', 'egg', 'bowl'] | skills ['action_recognition', 'event_object_role'] | time [130.75, 141.3] (4 narration(s), best score 9.5)
- s5e2 (action) Roll the egg-coated chicken ball in the breadcrumbs bowl. | objects ['chicken ball', 'breadcrumbs', 'bowl'] | skills ['action_recognition', 'event_object_role'] | time [130.75, 141.3] (4 narration(s), best score 10.0)

## sub-goal 6 [165.5-220.2, 55s] Form the second chicken ball and coat it with flour
- s6e1 (action) Shape the second chicken and cheese mixture into a ball. | objects ['chicken', 'cheese', 'hands'] | skills ['action_recognition', 'object_recognition'] | time [215.45, 220.06] (2 narration(s), best score 4.0)
- s6e2 (action) Roll the second chicken ball in the flour bowl. | objects ['chicken ball', 'flour', 'bowl'] | skills ['action_recognition', 'event_object_role'] | time [204.65, 205.17] (1 narration(s), best score 8.0)

## sub-goal 7 [220.3-232.8, 13s] Dip the second chicken ball in egg, sprinkle with more flour, and coat it with breadcrumbs
- s7e1 (action) Dip the second floured chicken ball into the egg bowl. | objects ['chicken ball', 'egg', 'bowl'] | skills ['action_recognition', 'event_object_role'] | time [219.66, 225.88] (4 narration(s), best score 9.5)
- s7e2 (action) Sprinkle extra flour onto the chicken ball. | objects ['flour', 'chicken ball'] | skills ['action_recognition', 'event_object_role'] | time [225.37, 228.77] (5 narration(s), best score 7.5)
- s7e3 (action) Roll the second chicken ball in the breadcrumbs bowl. | objects ['chicken ball', 'breadcrumbs', 'bowl'] | skills ['action_recognition', 'event_object_role'] | time [228.78, 232.78] (3 narration(s), best score 9.5)

## relations (L3)
- r1 object_continuity -> cross_event_integration: ['s1e1', 's2e1'] | ask: What was dispensed from the container before it was stored away? | hint: The container held breadcrumbs that were poured in the previous step.
- r2 causal_prerequisite -> causal_prerequisite_reasoning: ['s2e2', 's3e2'] | ask: Why was the empty bowl placed on the counter? | hint: It was placed to receive the flour poured in the next step.
- r3 causal_prerequisite -> causal_prerequisite_reasoning: ['s3e2', 's4e2'] | ask: What ingredient was added to the bowl before the chicken ball was rolled in it? | hint: Flour was poured into the bowl.
- r4 state_change -> cross_event_integration: ['s4e2', 's5e1'] | ask: What was the coating on the chicken ball just before it was dipped in the egg? | hint: It was coated in flour in the previous step.
- r5 object_continuity -> cross_event_integration: ['s5e2', 's6e1'] | ask: What was the person doing with the chicken mixture after finishing the first breaded ball? | hint: They started shaping a second ball from the same mixture.
- r6 state_change -> cross_event_integration: ['s6e2', 's7e1'] | ask: What was the coating on the second chicken ball just before it was dipped in the egg? | hint: It was coated in flour in the previous step.
- d1 object_continuity -> cross_event_integration: ['s4e2', 's5e2'] | ask: what happened to the shared object (ball, bowl, chicken) between the earlier event and the later one; what the later event shows that the earlier did not | hint: Roll the chicken ball in the flour bowl to coat it. -> Roll the egg-coated chicken ball in the breadcrumbs bowl.
- d2 object_continuity -> cross_event_integration: ['s5e1', 's6e2'] | ask: what happened to the shared object (ball, bowl, chicken) between the earlier event and the later one; what the later event shows that the earlier did not | hint: Dip the floured chicken ball into the egg bowl. -> Roll the second chicken ball in the flour bowl.
- d3 object_continuity -> cross_event_integration: ['s5e2', 's6e2'] | ask: what happened to the shared object (ball, bowl, chicken) between the earlier event and the later one; what the later event shows that the earlier did not | hint: Roll the egg-coated chicken ball in the breadcrumbs bowl. -> Roll the second chicken ball in the flour bowl.
- d4 object_continuity -> cross_event_integration: ['s6e2', 's7e2'] | ask: what happened to the shared object (ball, chicken, flour) between the earlier event and the later one; what the later event shows that the earlier did not | hint: Roll the second chicken ball in the flour bowl. -> Sprinkle extra flour onto the chicken ball.
- d5 object_continuity -> cross_event_integration: ['s6e2', 's7e3'] | ask: what happened to the shared object (ball, bowl, chicken) between the earlier event and the later one; what the later event shows that the earlier did not | hint: Roll the second chicken ball in the flour bowl. -> Roll the second chicken ball in the breadcrumbs bowl.
- d6 object_continuity -> cross_event_integration: ['s1e1', 's2e2'] | ask: what happened to the shared object (bowl) between the earlier event and the later one; what the later event shows that the earlier did not | hint: Pour breadcrumbs from the container into a bowl. -> Place an empty bowl on the counter for the flour.
- d7 object_continuity -> cross_event_integration: ['s1e2', 's2e2'] | ask: what happened to the shared object (bowl) between the earlier event and the later one; what the later event shows that the earlier did not | hint: The rustling sound of breadcrumbs hitting the bowl. -> Place an empty bowl on the counter for the flour.
- d8 object_continuity -> cross_event_integration: ['s2e1', 's3e1'] | ask: what happened to the shared object (cabinet) between the earlier event and the later one; what the later event shows that the earlier did not | hint: Place the breadcrumbs container away in a storage area. -> Take the flour from the cabinet.

## decision points (L4)
- idx 2 real=True: After setting up the breadcrumbs, the person must decide to store the container and prepare the next bowl rather than immediately starting to bread.
- idx 3 real=True: After placing the empty bowl, the person must decide to fetch the flour from the cabinet.
- idx 4 real=True: With the stations set up, the person decides to start forming the first chicken ball.
- idx 5 real=False: Dipping in egg and breadcrumbs is the standard, immediate continuation of the dredging process after flouring.
- idx 6 real=True: After finishing the first ball, the person must decide to repeat the process for a second ball.
- idx 7 real=False: Dipping the second ball in egg and breadcrumbs is the standard continuation of the dredging process.
- idx 8 real=True: After the second ball is fully coated, the person must decide what to do next, such as frying them, washing hands, or making a third ball.

## L1 pools
### spatial_near: 0 clusters (NOT_EVALUATED: no expected-event cluster for this skill on this task (sg mode))
### spatial_side: 0 clusters (NOT_EVALUATED: no expected-event cluster for this skill on this task (sg mode))
### object_recognition: 7 clusters
- sg1 win [6.31, 30.05] events ['s1e1', 's1e2'] anchors 6 core 7 bands {1:4, 2:2, 3:0, 4:0} knob ['n_other_narrations']
- sg2 win [30.15, 40.78] events ['s2e1', 's2e2'] anchors 10 core 12 bands {1:0, 2:3, 3:4, 4:3} knob ['n_other_narrations']
- sg3 win [40.91, 53.89] events ['s3e1', 's3e2'] anchors 12 core 14 bands {1:1, 2:0, 3:5, 4:6} knob ['n_other_narrations']
- sg4 win [74.02, 130.41] events ['s4e1', 's4e2'] anchors 16 core 18 bands {1:5, 2:1, 3:4, 4:6} knob ['n_other_narrations']
- sg5 win [130.75, 149.77] events ['s5e1', 's5e2'] anchors 6 core 8 bands {1:6, 2:0, 3:0, 4:0} knob ['n_other_narrations']
- sg6 win [165.52, 220.25] events ['s6e1', 's6e2'] anchors 18 core 19 bands {1:4, 2:10, 3:1, 4:3} knob ['n_other_narrations']
- sg7 win [220.27, 232.78] events ['s7e1', 's7e2', 's7e3'] anchors 11 core 13 bands {1:0, 2:4, 3:6, 4:1} knob ['n_other_narrations']
### object_location_at_time: 5 clusters
- sg2 win [30.15, 40.78] events ['s2e1', 's2e2'] anchors 2 core 11 bands {1:2, 2:0, 3:0, 4:0} knob ['area_neg']
- sg4 win [74.02, 130.41] events ['s4e1', 's4e2'] anchors 1 core 10 bands {1:0, 2:1, 3:0, 4:0} knob ['area_neg']
- sg5 win [130.75, 149.77] events ['s5e1', 's5e2'] anchors 1 core 7 bands {1:0, 2:0, 3:1, 4:0} knob ['area_neg']
- sg6 win [165.52, 220.25] events ['s6e1', 's6e2'] anchors 1 core 11 bands {1:0, 2:0, 3:1, 4:0} knob ['area_neg']
- sg7 win [220.27, 232.78] events ['s7e1', 's7e2', 's7e3'] anchors 1 core 6 bands {1:0, 2:0, 3:0, 4:1} knob ['area_neg']
### object_grounding: 16 clusters
- sg1 win [26.533, 27.533] events ['s1e1', 's1e2'] anchors 1 core 11 bands {1:0, 2:1, 3:0, 4:0} knob ['area_neg']
- sg1 win [30.3, 31.3] events ['s1e1', 's1e2'] anchors 1 core 13 bands {1:1, 2:0, 3:0, 4:0} knob ['area_neg']
- sg2 win [33.933, 34.933] events ['s2e1', 's2e2'] anchors 1 core 12 bands {1:0, 2:1, 3:0, 4:0} knob ['area_neg']
- sg2 win [37.033, 38.033] events ['s2e1', 's2e2'] anchors 1 core 14 bands {1:0, 2:1, 3:0, 4:0} knob ['area_neg']
- sg2 win [40.567, 41.567] events ['s2e1', 's2e2'] anchors 1 core 15 bands {1:0, 2:1, 3:0, 4:0} knob ['area_neg']
- sg4 win [81.667, 82.667] events ['s4e1', 's4e2'] anchors 1 core 17 bands {1:1, 2:0, 3:0, 4:0} knob ['area_neg']
- sg4 win [85.567, 86.567] events ['s4e1', 's4e2'] anchors 1 core 14 bands {1:0, 2:0, 3:0, 4:1} knob ['area_neg']
- sg4 win [92.333, 93.333] events ['s4e1', 's4e2'] anchors 1 core 6 bands {1:0, 2:0, 3:0, 4:1} knob ['area_neg']
- sg5 win [131.0, 132.0] events ['s5e1', 's5e2'] anchors 1 core 8 bands {1:0, 2:0, 3:1, 4:0} knob ['area_neg']
- sg5 win [136.767, 137.767] events ['s5e1', 's5e2'] anchors 1 core 8 bands {1:0, 2:0, 3:0, 4:1} knob ['area_neg']
- sg5 win [141.333, 142.333] events ['s5e1', 's5e2'] anchors 1 core 8 bands {1:0, 2:0, 3:1, 4:0} knob ['area_neg']
- sg6 win [201.433, 202.433] events ['s6e1', 's6e2'] anchors 1 core 10 bands {1:1, 2:0, 3:0, 4:0} knob ['area_neg']
- sg6 win [205.333, 206.333] events ['s6e1', 's6e2'] anchors 1 core 13 bands {1:1, 2:0, 3:0, 4:0} knob ['area_neg']
- sg6 win [220.4, 221.4] events ['s6e1', 's6e2'] anchors 1 core 13 bands {1:0, 2:0, 3:1, 4:0} knob ['area_neg']
- sg7 win [224.467, 225.467] events ['s7e1', 's7e2', 's7e3'] anchors 1 core 15 bands {1:0, 2:0, 3:1, 4:0} knob ['area_neg']
- sg7 win [230.433, 231.433] events ['s7e1', 's7e2', 's7e3'] anchors 1 core 12 bands {1:0, 2:0, 3:0, 4:1} knob ['area_neg']

## L2 pools
### sound_action_binding: 6 clusters
- sg1 win [6.31, 30.05] events ['s1e1', 's1e2'] anchors 2 core 10 tiers {1: 15.0, 2: 30.0, 3: 23.74, 4: 23.74}
- sg2 win [30.15, 40.78] events ['s2e1', 's2e2'] anchors 4 core 20 tiers {1: 15.0, 2: 30.0, 3: 10.63, 4: 10.63}
- sg4 win [74.02, 130.41] events ['s4e1', 's4e2'] anchors 6 core 27 tiers {1: 15.0, 2: 30.0, 3: 56.39, 4: 56.39}
- sg5 win [130.75, 149.77] events ['s5e1', 's5e2'] anchors 2 core 12 tiers {1: 15.0, 2: 30.0, 3: 19.02, 4: 19.02}
- sg6 win [165.52, 220.25] events ['s6e1', 's6e2'] anchors 10 core 33 tiers {1: 15.0, 2: 30.0, 3: 54.73, 4: 54.73}
- sg7 win [220.27, 232.78] events ['s7e1', 's7e2', 's7e3'] anchors 4 core 18 tiers {1: 15.0, 2: 30.0, 3: 12.51, 4: 12.51}
### object_state_change: 5 clusters
- sg2 win [30.15, 40.78] events ['s2e1', 's2e2'] anchors 2 core 13 tiers {1: 15.0, 2: 30.0, 3: 10.63, 4: 10.63}
- sg4 win [74.02, 130.41] events ['s4e1', 's4e2'] anchors 1 core 18 tiers {1: 15.0, 2: 30.0, 3: 56.39, 4: 56.39}
- sg5 win [130.75, 149.77] events ['s5e1', 's5e2'] anchors 1 core 8 tiers {1: 15.0, 2: 30.0, 3: 19.02, 4: 19.02}
- sg6 win [165.52, 220.25] events ['s6e1', 's6e2'] anchors 1 core 20 tiers {1: 15.0, 2: 30.0, 3: 54.73, 4: 54.73}
- sg7 win [220.27, 232.78] events ['s7e1', 's7e2', 's7e3'] anchors 1 core 13 tiers {1: 15.0, 2: 30.0, 3: 12.51, 4: 12.51}
### action_temporal_order: 7 clusters
- sg1 win [6.31, 30.05] events ['s1e1', 's1e2'] anchors 6 core 7 tiers {1: 15.0, 2: 30.0, 3: 23.74, 4: 23.74}
- sg2 win [30.15, 40.78] events ['s2e1', 's2e2'] anchors 10 core 11 tiers {1: 15.0, 2: 30.0, 3: 10.63, 4: 10.63}
- sg3 win [40.91, 53.89] events ['s3e1', 's3e2'] anchors 12 core 13 tiers {1: 15.0, 2: 30.0, 3: 12.98, 4: 12.98}
- sg4 win [74.02, 130.41] events ['s4e1', 's4e2'] anchors 16 core 17 tiers {1: 15.0, 2: 30.0, 3: 56.39, 4: 56.39}
- sg5 win [130.75, 149.77] events ['s5e1', 's5e2'] anchors 6 core 7 tiers {1: 15.0, 2: 30.0, 3: 19.02, 4: 19.02}
- sg6 win [165.52, 220.25] events ['s6e1', 's6e2'] anchors 18 core 19 tiers {1: 15.0, 2: 30.0, 3: 54.73, 4: 54.73}
- sg7 win [220.27, 232.78] events ['s7e1', 's7e2', 's7e3'] anchors 11 core 12 tiers {1: 15.0, 2: 30.0, 3: 12.51, 4: 12.51}
### action_recognition: 7 clusters
- sg1 win [6.31, 30.05] events ['s1e1', 's1e2'] anchors 6 core 8 tiers {1: 15.0, 2: 30.0, 3: 23.74, 4: 23.74}
- sg2 win [30.15, 40.78] events ['s2e1', 's2e2'] anchors 10 core 16 tiers {1: 15.0, 2: 30.0, 3: 10.63, 4: 10.63}
- sg3 win [40.91, 53.89] events ['s3e1', 's3e2'] anchors 12 core 14 tiers {1: 15.0, 2: 30.0, 3: 12.98, 4: 12.98}
- sg4 win [74.02, 130.41] events ['s4e1', 's4e2'] anchors 16 core 21 tiers {1: 15.0, 2: 30.0, 3: 56.39, 4: 56.39}
- sg5 win [130.75, 149.77] events ['s5e1', 's5e2'] anchors 6 core 10 tiers {1: 15.0, 2: 30.0, 3: 19.02, 4: 19.02}
- sg6 win [165.52, 220.25] events ['s6e1', 's6e2'] anchors 18 core 23 tiers {1: 15.0, 2: 30.0, 3: 54.73, 4: 54.73}
- sg7 win [220.27, 232.78] events ['s7e1', 's7e2', 's7e3'] anchors 11 core 14 tiers {1: 15.0, 2: 30.0, 3: 12.51, 4: 12.51}
### event_object_role: 7 clusters
- sg1 win [6.31, 30.05] events ['s1e1', 's1e2'] anchors 6 core 8 tiers {1: 15.0, 2: 30.0, 3: 23.74, 4: 23.74}
- sg2 win [30.15, 40.78] events ['s2e1', 's2e2'] anchors 9 core 16 tiers {1: 15.0, 2: 30.0, 3: 10.63, 4: 10.63}
- sg3 win [40.91, 53.89] events ['s3e1', 's3e2'] anchors 12 core 14 tiers {1: 15.0, 2: 30.0, 3: 12.98, 4: 12.98}
- sg4 win [74.02, 130.41] events ['s4e1', 's4e2'] anchors 16 core 21 tiers {1: 15.0, 2: 30.0, 3: 56.39, 4: 56.39}
- sg5 win [130.75, 149.77] events ['s5e1', 's5e2'] anchors 6 core 10 tiers {1: 15.0, 2: 30.0, 3: 19.02, 4: 19.02}
- sg6 win [165.52, 220.25] events ['s6e1', 's6e2'] anchors 17 core 23 tiers {1: 15.0, 2: 30.0, 3: 54.73, 4: 54.73}
- sg7 win [220.27, 232.78] events ['s7e1', 's7e2', 's7e3'] anchors 11 core 14 tiers {1: 15.0, 2: 30.0, 3: 12.51, 4: 12.51}
### sound_anchored_spatial_near: 0 clusters (NOT_EVALUATED: no expected-event cluster for this skill on this task (sg mode))
### sound_anchored_spatial_side: 0 clusters (NOT_EVALUATED: no expected-event cluster for this skill on this task (sg mode))
### sound_movement_binding: 5 clusters
- sg2 win [30.15, 40.78] events ['s2e1', 's2e2'] anchors 4 core 8 tiers {1: 15.0, 2: 30.0, 3: 10.63, 4: 10.63}
- sg4 win [74.02, 130.41] events ['s4e1', 's4e2'] anchors 6 core 10 tiers {1: 15.0, 2: 30.0, 3: 56.39, 4: 56.39}
- sg5 win [130.75, 149.77] events ['s5e1', 's5e2'] anchors 2 core 5 tiers {1: 15.0, 2: 30.0, 3: 19.02, 4: 19.02}
- sg6 win [165.52, 220.25] events ['s6e1', 's6e2'] anchors 10 core 14 tiers {1: 15.0, 2: 30.0, 3: 54.73, 4: 54.73}
- sg7 win [220.27, 232.78] events ['s7e1', 's7e2', 's7e3'] anchors 4 core 6 tiers {1: 15.0, 2: 30.0, 3: 12.51, 4: 12.51}

## L3 pools
### cross_event_integration: 48 clusters
- r1 (planner) tier 1 sub-goals [1, 2] win [6.31, 40.78] (34.5s, sub-goal k and k+1 only) in-clip [1, 2] core 29
- r1 (planner) tier 2 sub-goals [1, 2] win [6.31, 53.89] (47.6s, previous + the pair + next sub-goal) in-clip [1, 2, 3] core 38
- r1 (planner) tier 3 sub-goals [1, 2] win [0.0, 113.545] (113.5s, 180 s centred on the pair, single choice) in-clip [1, 2, 3, 4] core 39
- r1 (planner) tier 4 sub-goals [1, 2] win [0.0, 113.545] (113.5s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4] core 39
- r4 (planner) tier 1 sub-goals [4, 5] win [74.02, 149.77] (75.8s, sub-goal k and k+1 only) in-clip [4, 5] core 41
- r4 (planner) tier 2 sub-goals [4, 5] win [40.91, 220.25] (179.3s, previous + the pair + next sub-goal) in-clip [3, 4, 5, 6] core 43
- r4 (planner) tier 3 sub-goals [4, 5] win [40.91, 220.25] (179.3s, 180 s centred on the pair, single choice) in-clip [3, 4, 5, 6] core 43
- r4 (planner) tier 4 sub-goals [4, 5] win [21.895, 201.895] (180.0s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4, 5, 6] core 45
- r5 (planner) tier 1 sub-goals [5, 6] win [130.75, 220.25] (89.5s, sub-goal k and k+1 only) in-clip [5, 6] core 27
- r5 (planner) tier 2 sub-goals [5, 6] win [74.02, 232.78] (158.8s, previous + the pair + next sub-goal) in-clip [4, 5, 6, 7] core 37
- r5 (planner) tier 3 sub-goals [5, 6] win [85.5, 265.5] (180.0s, 180 s centred on the pair, single choice) in-clip [4, 5, 6, 7] core 37
- r5 (planner) tier 4 sub-goals [5, 6] win [85.5, 265.5] (180.0s, 180 s centred on the pair, short answer) in-clip [4, 5, 6, 7] core 37
- r6 (planner) tier 1 sub-goals [6, 7] win [165.52, 232.78] (67.3s, sub-goal k and k+1 only) in-clip [6, 7] core 46
- r6 (planner) tier 2 sub-goals [6, 7] win [130.75, 232.78] (102.0s, previous + the pair + next sub-goal) in-clip [5, 6, 7] core 47
- r6 (planner) tier 3 sub-goals [6, 7] win [109.15, 289.15] (180.0s, 180 s centred on the pair, single choice) in-clip [4, 5, 6, 7] core 48
- r6 (planner) tier 4 sub-goals [6, 7] win [109.15, 289.15] (180.0s, 180 s centred on the pair, short answer) in-clip [4, 5, 6, 7] core 48
- d1 (derived) tier 1 sub-goals [4, 5] win [74.02, 149.77] (75.8s, sub-goal k and k+1 only) in-clip [4, 5] core 41
- d1 (derived) tier 2 sub-goals [4, 5] win [40.91, 220.25] (179.3s, previous + the pair + next sub-goal) in-clip [3, 4, 5, 6] core 43
- d1 (derived) tier 3 sub-goals [4, 5] win [40.91, 220.25] (179.3s, 180 s centred on the pair, single choice) in-clip [3, 4, 5, 6] core 43
- d1 (derived) tier 4 sub-goals [4, 5] win [21.895, 201.895] (180.0s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4, 5, 6] core 45
- d2 (derived) tier 1 sub-goals [5, 6] win [130.75, 220.25] (89.5s, sub-goal k and k+1 only) in-clip [5, 6] core 32
- d2 (derived) tier 2 sub-goals [5, 6] win [74.02, 232.78] (158.8s, previous + the pair + next sub-goal) in-clip [4, 5, 6, 7] core 35
- d2 (derived) tier 3 sub-goals [5, 6] win [85.5, 265.5] (180.0s, 180 s centred on the pair, single choice) in-clip [4, 5, 6, 7] core 35
- d2 (derived) tier 4 sub-goals [5, 6] win [85.5, 265.5] (180.0s, 180 s centred on the pair, short answer) in-clip [4, 5, 6, 7] core 35
- d3 (derived) tier 1 sub-goals [5, 6] win [130.75, 220.25] (89.5s, sub-goal k and k+1 only) in-clip [5, 6] core 32
- d3 (derived) tier 2 sub-goals [5, 6] win [74.02, 232.78] (158.8s, previous + the pair + next sub-goal) in-clip [4, 5, 6, 7] core 35
- d3 (derived) tier 3 sub-goals [5, 6] win [85.5, 265.5] (180.0s, 180 s centred on the pair, single choice) in-clip [4, 5, 6, 7] core 35
- d3 (derived) tier 4 sub-goals [5, 6] win [85.5, 265.5] (180.0s, 180 s centred on the pair, short answer) in-clip [4, 5, 6, 7] core 35
- d4 (derived) tier 1 sub-goals [6, 7] win [165.52, 232.78] (67.3s, sub-goal k and k+1 only) in-clip [6, 7] core 38
- d4 (derived) tier 2 sub-goals [6, 7] win [130.75, 232.78] (102.0s, previous + the pair + next sub-goal) in-clip [5, 6, 7] core 39
- d4 (derived) tier 3 sub-goals [6, 7] win [109.15, 289.15] (180.0s, 180 s centred on the pair, single choice) in-clip [4, 5, 6, 7] core 40
- d4 (derived) tier 4 sub-goals [6, 7] win [109.15, 289.15] (180.0s, 180 s centred on the pair, short answer) in-clip [4, 5, 6, 7] core 40
- d5 (derived) tier 1 sub-goals [6, 7] win [165.52, 232.78] (67.3s, sub-goal k and k+1 only) in-clip [6, 7] core 34
- d5 (derived) tier 2 sub-goals [6, 7] win [130.75, 232.78] (102.0s, previous + the pair + next sub-goal) in-clip [5, 6, 7] core 35
- d5 (derived) tier 3 sub-goals [6, 7] win [109.15, 289.15] (180.0s, 180 s centred on the pair, single choice) in-clip [4, 5, 6, 7] core 38
- d5 (derived) tier 4 sub-goals [6, 7] win [109.15, 289.15] (180.0s, 180 s centred on the pair, short answer) in-clip [4, 5, 6, 7] core 38
- d6 (derived) tier 1 sub-goals [1, 2] win [6.31, 40.78] (34.5s, sub-goal k and k+1 only) in-clip [1, 2] core 29
- d6 (derived) tier 2 sub-goals [1, 2] win [6.31, 53.89] (47.6s, previous + the pair + next sub-goal) in-clip [1, 2, 3] core 32
- d6 (derived) tier 3 sub-goals [1, 2] win [0.0, 113.545] (113.5s, 180 s centred on the pair, single choice) in-clip [1, 2, 3, 4] core 33
- d6 (derived) tier 4 sub-goals [1, 2] win [0.0, 113.545] (113.5s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4] core 33
- d7 (derived) tier 1 sub-goals [1, 2] win [6.31, 40.78] (34.5s, sub-goal k and k+1 only) in-clip [1, 2] core 29
- d7 (derived) tier 2 sub-goals [1, 2] win [6.31, 53.89] (47.6s, previous + the pair + next sub-goal) in-clip [1, 2, 3] core 32
- d7 (derived) tier 3 sub-goals [1, 2] win [0.0, 113.545] (113.5s, 180 s centred on the pair, single choice) in-clip [1, 2, 3, 4] core 33
- d7 (derived) tier 4 sub-goals [1, 2] win [0.0, 113.545] (113.5s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4] core 33
- d8 (derived) tier 1 sub-goals [2, 3] win [30.15, 53.89] (23.7s, sub-goal k and k+1 only) in-clip [2, 3] core 36
- d8 (derived) tier 2 sub-goals [2, 3] win [6.31, 130.41] (124.1s, previous + the pair + next sub-goal) in-clip [1, 2, 3, 4] core 48
- d8 (derived) tier 3 sub-goals [2, 3] win [0.0, 132.02] (132.0s, 180 s centred on the pair, single choice) in-clip [1, 2, 3, 4, 5] core 49
- d8 (derived) tier 4 sub-goals [2, 3] win [0.0, 132.02] (132.0s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4, 5] core 49
### hidden_state_inference: 0 clusters (NOT_EVALUATED: no expected-event cluster for this skill on this task (sg mode))
### spatial_state_integration: 0 clusters (NOT_EVALUATED: no expected-event cluster for this skill on this task (sg mode))
### causal_prerequisite_reasoning: 8 clusters
- r2 (planner) tier 1 sub-goals [2, 3] win [30.15, 53.89] (23.7s, sub-goal k and k+1 only) in-clip [2, 3] core 36
- r2 (planner) tier 2 sub-goals [2, 3] win [6.31, 130.41] (124.1s, previous + the pair + next sub-goal) in-clip [1, 2, 3, 4] core 48
- r2 (planner) tier 3 sub-goals [2, 3] win [0.0, 132.02] (132.0s, 180 s centred on the pair, single choice) in-clip [1, 2, 3, 4, 5] core 49
- r2 (planner) tier 4 sub-goals [2, 3] win [0.0, 132.02] (132.0s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4, 5] core 49
- r3 (planner) tier 1 sub-goals [3, 4] win [40.91, 130.41] (89.5s, sub-goal k and k+1 only) in-clip [3, 4] core 46
- r3 (planner) tier 2 sub-goals [3, 4] win [30.15, 149.77] (119.6s, previous + the pair + next sub-goal) in-clip [2, 3, 4, 5] core 48
- r3 (planner) tier 3 sub-goals [3, 4] win [0.0, 175.66] (175.7s, 180 s centred on the pair, single choice) in-clip [1, 2, 3, 4, 5, 6] core 50
- r3 (planner) tier 4 sub-goals [3, 4] win [0.0, 175.66] (175.7s, 180 s centred on the pair, short answer) in-clip [1, 2, 3, 4, 5, 6] core 50

## L4 pools
### goal_conditioned_planning: 5 clusters
- decision idx 2 win [6.31, 30.15] cutoff 30.15 remaining 6 final=False core 35
- decision idx 3 win [30.15, 40.91] cutoff 40.91 remaining 5 final=False core 17
- decision idx 4 win [40.91, 74.02] cutoff 74.02 remaining 4 final=False core 35
- decision idx 6 win [130.75, 165.52] cutoff 165.52 remaining 2 final=False core 26
- decision idx 8 win [220.27, 232.78] cutoff 232.78 remaining 0 final=True core 20

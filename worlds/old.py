# #NOTE:
# # initializing Items
# # Study Room Items
# personal_diary = Item(
#     name="personal_diary",
#     description="A leather-bound diary with gold-trimmed pages, ready to record thoughts and memories.",
#     interactions={
#         "read": None,
#         "write": {"content": str},
#         "inspect": None
#     },
#     properties={
#         "content": "Dear Diary, today I began my journey in this mysterious place..."
#     }
# )
#
# # Kitchen Items
# cooking_pot = Item(
#     name="cooking_pot",
#     description="A large copper pot with a sturdy handle, perfect for cooking hearty meals.",
#     interactions={
#         "cook": {"ingredient": str},
#         "examine": None,
#         "clean": None
#     },
#     properties={
#         "contents": "",
#         "is_clean": True
#     }
# )
#
# # Garden Items
# watering_can = Item(
#     name="watering_can",
#     description="A painted metal watering can with a long spout, ideal for tending to plants.",
#     interactions={
#         "fill": None,
#         "water": {"plant": str},
#         "inspect": None
#     },
#     properties={
#         "water_level": 0,
#         "max_capacity": 10
#     }
# )
#
# # Basement Items
# mysterious_device = Item(
#     name="mysterious_device",
#     description="A strange mechanical contraption with gears, buttons, and blinking lights of unknown purpose.",
#     interactions={
#         "activate": None,
#         "adjust": {"setting": str},
#         "disassemble": None,
#         "inspect": None
#     },
#     properties={
#         "is_active": False,
#         "current_setting": "standby",
#         "energy_level": 75
#     }
# )
#
#
# ancient_book = Item(
#     name="ancient_book",
#     description="A weathered tome bound in mysterious symbols, its pages filled with fascinating stories.",
#     interactions={
#         "read": None,
#         "inspect": None
#     },
#     properties={
#         "content": "In the age of wonders, when magic still flowed freely through the world..."
#     }
# )
#
# # Living Room Items
# music_box = Item(
#     name="music_box",
#     description="An ornate music box decorated with dancing figures, capable of playing enchanting melodies.",
#     interactions={
#         "play": None,
#         "stop": None,
#         "inspect": None
#     },
#     properties={
#         "is_playing": False
#     }
# )
#
# mirror = Item(
#     name="mirror",
#     description="An elegant full-length mirror in a gilded frame, reflecting the room with perfect clarity.",
#     interactions={
#         "inspect": None
#     },
#     properties={}
# )
#
#
# #NOTE:
# # Initialize Spaces with their items
# study_room = Space(
#     name="study_room",
#     description=(
#         "A cozy study lined with wooden bookshelves. Warm lamplight creates a perfect "
#         "atmosphere for reading and writing. A personal diary rests on the desk, and "
#         "an ancient book catches your eye from one of the shelves."
#     ),
#     items=[personal_diary, ancient_book]
# )
#
# living_room = Space(
#     name="living_room",
#     description=(
#         "An elegant living room with plush furnishings. Sunlight streams through tall windows, "
#         "making the ornate music box gleam. A beautiful mirror stands in the corner, "
#         "adding depth to the room."
#     ),
#     items=[music_box, mirror]
# )
#
# # Kitchen Items
# cookbook = Item(
#     name="cookbook",
#     description="A well-used cookbook with handwritten notes in the margins and dog-eared pages marking favorite recipes.",
#     interactions={
#         "read": None,
#         "inspect": None
#     },
#     properties={}
# )
#
# tea_set = Item(
#     name="tea_set",
#     description="A delicate porcelain tea set with floral patterns, perfect for brewing and serving tea.",
#     interactions={
#         "use": None,
#         "inspect": None
#     },
#     properties={
#         "is_brewing": False
#     }
# )
#
# # Garden Items
# watering_can = Item(
#     name="watering_can",
#     description="A copper watering can with a long spout, ideal for tending to the garden plants.",
#     interactions={
#         "use": None,
#         "inspect": None
#     },
#     properties={
#         "is_filled": True
#     }
# )
#
# stone_bench = Item(
#     name="stone_bench",
#     description="A weathered stone bench nestled among flowering plants, offering a peaceful spot for contemplation.",
#     interactions={
#         "sit": None,
#         "inspect": None
#     },
#     properties={}
# )
#
# # Attic Items
# old_chest = Item(
#     name="old_chest",
#     description="A dusty wooden chest with iron fittings, locked and seemingly untouched for years.",
#     interactions={
#         "open": None,
#         "inspect": None
#     },
#     properties={
#         "is_locked": True
#     }
# )
#
# telescope = Item(
#     name="telescope",
#     description="An antique brass telescope mounted by the window, pointing toward the night sky.",
#     interactions={
#         "use": None,
#         "adjust": None,
#         "inspect": None
#     },
#     properties={
#         "is_focused": False
#     }
# )
#
# # Initialize the new spaces
# kitchen = Space(
#     name="kitchen",
#     description=(
#         "A warm, inviting kitchen with copper pots hanging from the ceiling and sunlight "
#         "streaming through a window above the sink. A cookbook rests on the counter next "
#         "to a beautiful tea set, ready for use."
#     ),
#     items=[cookbook, tea_set]
# )
#
# garden = Space(
#     name="garden",
#     description=(
#         "A lush garden bursting with colorful flowers and aromatic herbs. Stone pathways "
#         "wind through the greenery, leading to a peaceful stone bench. A copper watering "
#         "can sits ready for tending to the plants."
#     ),
#     items=[watering_can, stone_bench]
# )
#
# attic = Space(
#     name="attic",
#     description=(
#         "A spacious attic filled with dust motes dancing in beams of light from a small "
#         "round window. An old wooden chest sits in one corner, while a brass telescope "
#         "stands by the window, pointed at the sky."
#     ),
#     items=[old_chest, telescope]
# )
# basement = Space(
#     name="basement",
#     description=(
#         "A dimly lit basement with stone walls and a slightly damp atmosphere. Shelves line "
#         "the walls, filled with old bottles and curious artifacts. In the center stands a "
#         "mysterious device with blinking lights and intricate gears."
#     ),
#     items=[mysterious_device]
# )
#
# # Connect all spaces in a logical layout
# living_room.biconnect(kitchen)
# living_room.biconnect(garden)
# study_room.biconnect(attic)
# living_room.biconnect(basement)
#
#
# # Connect the spaces
# study_room.biconnect(living_room)
#
# #NOTE: Instance of an NPC
# # 創建 NPC
# # Initializing Arthur
#
# arthur = NPC(
#     name="arthur",
#     description="A curious and thoughtful explorer with a keen interest in uncovering stories and mysteries.",
#     current_space=living_room,
#     inventory=Inventory(items=[]),
#     history=[
#         {
#             "role": "system", 
#             "content": """You are Arthur, a curious explorer who has found yourself in an intriguing house.
#             You can:
#             - Explore different rooms
#             - Interact with items you find
#             - Record your thoughts in the diary if you find one
#             - Enjoy music from the music box
#             
#             You have a particular interest in:
#             - Writing down your observations and feelings
#             - Understanding the stories behind items you find
#             - Creating a peaceful atmosphere with music
#             
#             Take your time to explore and interact with your surroundings."""
#         },
#         {
#             "role": "assistant", 
#             "content": "I find myself in this interesting house. I should explore and interact with what I find. I wanna explore other spaces"
#         }
#     ]
# )
#
# # Add Arthur to his starting space's NPCs list
# living_room.npcs.append(arthur)


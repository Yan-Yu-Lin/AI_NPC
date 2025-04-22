from AI_thinking import AIThinking
import json

class DummyNPC:
    pass

if __name__ == "__main__":
    npc = DummyNPC()
    npc.current_space = 'kitchen'
    ai = AIThinking(npc, None, None, map_path='worlds/new_save.json')
    ai.set_npc_available_spaces_from_save(npc)
    print('npc.available_spaces =', getattr(npc, 'available_spaces', None))

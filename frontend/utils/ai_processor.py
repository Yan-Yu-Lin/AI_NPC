"""
AIProcessor - Handles AI processing in separate threads

This class manages AI calls to prevent blocking the main game loop.
"""

import threading
from typing import Dict, Optional
from queue import Queue

from interfaces import BackendAPI, UserInput


class AIProcessor:
    """
    Manages AI processing in separate threads.
    
    This prevents AI calls from blocking the main game loop and
    provides status updates during processing.
    """
    
    def __init__(self, backend_api: BackendAPI):
        """
        Initialize the AI processor.
        
        Args:
            backend_api: Backend API for AI processing
        """
        self.backend_api = backend_api
        self.processing_threads: Dict[str, threading.Thread] = {}
        self.processing_status: Dict[str, bool] = {}
        self.result_queue = Queue()
        
    def process_npc(self, npc_id: str):
        """
        Process AI for an NPC without user input.
        
        Args:
            npc_id: NPC identifier
        """
        if self.is_processing(npc_id):
            return
        
        self.processing_status[npc_id] = True
        
        thread = threading.Thread(
            target=self._process_thread,
            args=(npc_id, None),
            daemon=True
        )
        self.processing_threads[npc_id] = thread
        thread.start()
    
    def process_npc_with_input(self, npc_id: str, user_text: str):
        """
        Process AI for an NPC with user input.
        
        Args:
            npc_id: NPC identifier
            user_text: User input text
        """
        if self.is_processing(npc_id):
            return
        
        self.processing_status[npc_id] = True
        
        thread = threading.Thread(
            target=self._process_thread,
            args=(npc_id, user_text),
            daemon=True
        )
        self.processing_threads[npc_id] = thread
        thread.start()
    
    def is_processing(self, npc_id: str) -> bool:
        """
        Check if an NPC is currently being processed.
        
        Args:
            npc_id: NPC identifier
            
        Returns:
            True if processing, False otherwise
        """
        return self.processing_status.get(npc_id, False)
    
    def stop(self):
        """Stop all processing threads."""
        # Wait for all threads to complete
        for thread in self.processing_threads.values():
            if thread.is_alive():
                thread.join(timeout=1.0)
    
    def _process_thread(self, npc_id: str, user_text: Optional[str]):
        """
        Thread function for processing AI.
        
        Args:
            npc_id: NPC identifier
            user_text: Optional user input
        """
        try:
            # Process through backend API
            if user_text:
                user_input = UserInput(
                    npc_id=npc_id,
                    input_type="text",
                    content=user_text
                )
                result = self.backend_api.process_user_input(user_input)
            else:
                result = self.backend_api.trigger_npc_action(npc_id)
            
            # Store result
            self.result_queue.put((npc_id, result))
            
        except Exception as e:
            print(f"Error processing AI for {npc_id}: {e}")
            self.result_queue.put((npc_id, None))
        
        finally:
            self.processing_status[npc_id] = False
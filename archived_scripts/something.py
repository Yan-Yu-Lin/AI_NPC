    def process_interaction(self, npc: "NPC", target_item_name: str, inventory_item_names: List[str], how_to_interact: str) -> str:
        """
        處理 NPC 與物品的互動。
        根據 NPC 的意圖、涉及的物品以及當前世界狀態，調用 LLM 來決定如何修改世界，
        並執行相應的操作。

        Args:
            npc: 執行互動的 NPC 物件。
            target_item_name: NPC 主要互動的目標物品的名稱。
            inventory_item_names: NPC 從其庫存中選取用於此次互動的輔助物品的名稱列表。
            how_to_interact: NPC 描述它希望如何與這些物品互動的自然語言字串。

        Returns:
            一個描述互動結果的自然語言字串，將回傳給 NPC。
        """
        global client # 假設 OpenAI client 是全局可用的

        # --- 1. 獲取並驗證互動中涉及的所有物品實體 ---
        target_item_object: Optional[Item] = None
        item_location_info = ""

        # 首先在 NPC 當前空間查找目標物品
        for item_in_space in npc.current_space.items:
            if item_in_space.name == target_item_name:
                target_item_object = item_in_space
                item_location_info = f"目標物品 '{target_item_name}' 位於空間 '{npc.current_space.name}'。"
                break
        
        # 如果空間中沒有，則在 NPC 庫存中查找 (某些情況下 NPC 可能以自身物品為主目標)
        if not target_item_object:
            for item_in_inv in npc.inventory.items:
                if item_in_inv.name == target_item_name:
                    target_item_object = item_in_inv
                    item_location_info = f"目標物品 '{target_item_name}' 位於 NPC '{npc.name}' 的庫存中。"
                    break
        
        if not target_item_object:
            return f"系統錯誤：找不到名為 '{target_item_name}' 的目標物品。互動中止。"

        list_of_inventory_item_objects: List[Item] = []
        inventory_items_info_lines = []
        if inventory_item_names:
            inventory_items_info_lines.append("NPC 使用的庫存物品：")
            for inv_item_name in inventory_item_names:
                found_inv_item = False
                for item_obj in npc.inventory.items:
                    if item_obj.name == inv_item_name:
                        list_of_inventory_item_objects.append(item_obj)
                        inventory_items_info_lines.append(f"- '{item_obj.name}' (描述：'{item_obj.description}')")
                        found_inv_item = True
                        break
                if not found_inv_item:
                    # 如果有輔助物品找不到，可以選擇中止或忽略該物品並繼續
                    # 這裡選擇中止以保證互動的嚴謹性
                    return f"系統錯誤：NPC '{npc.name}' 的庫存中找不到名為 '{inv_item_name}' 的物品。互動中止。"

        # --- 2. 準備傳遞給 update_schema 的物品名稱列表 ---
        # available_items_for_interaction: 本次互動明確涉及的所有物品
        available_items_for_interaction = [target_item_object.name] + [item.name for item in list_of_inventory_item_objects]
        
        # npc_complete_inventory: NPC 的完整庫存列表
        npc_complete_inventory = [item.name for item in npc.inventory.items]

        # --- 3. 動態生成 AI_System 使用的 Schema ---
        DynamicSchemaToUse = self.update_schema(available_items_for_interaction, npc_complete_inventory)

        # --- 4. 建構詳細的互動上下文 (Context) 給 LLM ---
        context_lines = [
            f"NPC '{npc.name}' (描述：'{npc.description}') 正在嘗試執行以下操作：'{how_to_interact}'.",
            item_location_info,
            f"主要目標物品詳細資訊：'{target_item_object.name}' (描述：'{target_item_object.description}', 屬性：{target_item_object.properties})."
        ]
        context_lines.extend(inventory_items_info_lines)
        context_lines.append(f"目前世界時間：{self.time}, 天氣：{self.weather}.")
        context_lines.append("NPC 的完整庫存列表為：" + (', '.join(npc_complete_inventory) if npc_complete_inventory else "空的"))
        context_lines.append(f"本次互動明確涉及的物品有：{', '.join(available_items_for_interaction)}")
        
        # 可以考慮加入 AI_System 的部分歷史記錄，如果認為有助於 LLM 判斷
        # relevant_history = self.history[-5:] # 例如最近5條
        # context_lines.append("系統最近的相關操作歷史：")
        # for entry in relevant_history:
        #     context_lines.append(f"- [{entry.get('role','unknown')}] {entry.get('content','no content')}")

        interaction_prompt_content = "\n".join(context_lines)
        
        messages_for_llm = [
            {"role": "system", "content": "你是一個負責根據 NPC 意圖和世界狀態來決定如何修改遊戲世界的 AI 系統。請仔細分析以下提供的完整情境，然後根據你的理解，選擇一個最合適的 `function` 來執行，同時提供你的 `reasoning`（思考過程）和給 NPC 的 `response_to_AI`（自然語言回應）。如果 NPC 的意圖不需要改變世界物品狀態（例如只是觀察），則 `function` 應該為 `None`。"},
            {"role": "user", "content": interaction_prompt_content}
        ]
        
        print("\n=== AI_System 向 LLM 發送的內容 ===")
        print(interaction_prompt_content)
        print("================================\n")

        # --- 5. 呼叫 LLM 並使用動態 Schema 解析回應 ---
        try:
            completion = client.beta.chat.completions.parse(
                model="gpt-4o", # 或者您環境中配置的模型
                messages=messages_for_llm,
                response_format=DynamicSchemaToUse # 使用動態生成的 Schema
            )
            ai_system_response = completion.choices[0].message.parsed
        except Exception as e:
            error_msg = f"AI_System在與LLM溝通或解析回應時發生錯誤: {str(e)}"
            print(f"[錯誤] {error_msg}")
            # 發生錯誤時，可以考慮返回一個通用的錯誤提示給NPC
            return f"我現在有點糊塗，暫時無法完成 '{how_to_interact}' 這個操作。"

        print("\n=== AI_System 從 LLM 收到的原始回應 (parsed) ===")
        print(ai_system_response)
        print("===========================================\n")

        # --- 6. 記錄 AI_System 的思考和給 NPC 的回應到其歷史 ---
        self.history.append({
            "role": "assistant", # 代表 AI_System 自身的活動
            "content": f"針對NPC '{npc.name}' 的意圖 '{how_to_interact}' (涉及物品: {', '.join(available_items_for_interaction)}):\n  系統思考: {ai_system_response.reasoning}\n  計劃給NPC的回應: {ai_system_response.response_to_AI}"
        })

        # --- 7. 處理 AI_System.Function 呼叫 ---
        function_execution_details = "沒有執行功能。"
        if ai_system_response.function:
            try:
                # 注意：ai_system_response.function 將是 update_schema 內部定義的那些類的實例
                function_execution_details = self._handle_function(ai_system_response.function, npc, available_items_for_interaction)
                self.history.append({
                    "role": "system", # 標記這是系統執行內部功能的日誌
                    "content": f"系統執行功能 (由NPC '{npc.name}' 觸發，意圖: '{how_to_interact}'):\n  功能類型: {str(ai_system_response.function.function_type if hasattr(ai_system_response.function, 'function_type') else '未知')}\n  功能參數: {str(ai_system_response.function.model_dump(exclude_none=True))}\n  執行結果: {function_execution_details}"
                })
            except Exception as e:
                error_msg = f"AI_System在執行內部功能 '{str(ai_system_response.function.function_type if hasattr(ai_system_response.function, 'function_type') else '未知')}' 時發生錯誤: {str(e)}"
                print(f"[錯誤] {error_msg}")
                self.history.append({"role": "system", "content": f"[錯誤日誌] {error_msg}"})
                # 功能執行失敗，可以考慮修改 response_to_AI 或返回特定的錯誤訊息
                # 這裡暫時仍然返回 LLM 原本想給的回應，但實際應用中可能需要更細緻的錯誤處理
                return f"我在嘗試 '{how_to_interact}' 的時候遇到了一些內部問題，可能沒有完全成功。"

        # --- 8. 返回給 NPC 的結果 ---
        # 可以在這裡根據 function_execution_details 的內容，對 ai_system_response.response_to_AI 做一些微調，
        # 例如，如果功能執行結果中包含了一些重要的成功或失敗信息，可以附加到 response_to_AI 中。
        # 但簡單起見，我們先直接返回 LLM 生成的回應。
        return ai_system_response.response_to_AI

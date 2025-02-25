#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Restyaboard -> Trello 轉換工具
==================================
此腳本用於將 Restyaboard 的 JSON 輸出，轉換成 Trello 可以匯入的 JSON 格式。

使用方式：
    python restya2trello.py <restyaboard_input.json> [trello_output.json]

若無指定 trello_output.json，則預設輸出為 trello_export.json。
"""

import sys
import json
import hashlib
import datetime

# Restyaboard -> Trello color & name mapping
# 若 Restyaboard label.color 與此處 HEX 相符，則轉成 trello_color & label_name
COLOR_MAPPING = {
    "#0091ff": {
        "trello_color": "blue",
        "label_name": "INFO"
    },
    "#baa1e6": {
        "trello_color": "purple",
        "label_name": "FETAL"
    },
    "#f47564": {
        "trello_color": "red",
        "label_name": "CRITICAL"
    },
    "#f7b09c": {
        "trello_color": "pink",
        "label_name": "ERROR"
    },
    "#ffce54": {
        "trello_color": "orange",
        "label_name": "WARNING"
    }
}

def gen_trello_id(value):
    """
    為整數或字串產生一個 24 字元長度的 Hex 字串，用以模擬 Trello ID。
    :param value: 可為任何整數或字串
    :return: 長度 24 的 hex 字串
    """
    md5_hash = hashlib.md5(str(value).encode()).hexdigest()
    return md5_hash[:24]

def gen_short_link(value):
    """
    為輸入字串產生 8 字元 shortLink。
    :param value: 字串
    :return: 長度 8 的 hex 字串
    """
    md5_hash = hashlib.md5(value.encode()).hexdigest()
    return md5_hash[:8]

def normalize_due(due_value):
    """
    若 due 不以 'Z' 結尾，則在末尾加上 'Z'。
    :param due_value: 日期字串
    :return: 加上 'Z' 後的日期字串
    """
    if due_value and not due_value.endswith("Z"):
        return due_value + "Z"
    return due_value

def main():
    """
    主程式流程：
    1. 讀取命令列參數，取得 Restyaboard 的 JSON 檔案路徑與輸出檔案路徑。
    2. 若無資料，直接輸出基礎的空 Trello JSON 結構。
    3. 否則，依序轉換 board、lists、cards、labels、checklists 等資訊，最後輸出 Trello JSON。
    """
    if len(sys.argv) < 2:
        print("Usage: python3 restya2trello.py <restyaboard_input.json> [trello_output.json]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = "trello_export.json"
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    # 讀取 Restyaboard JSON
    with open(input_file, "r", encoding="utf-8") as f:
        restya_data = json.load(f)

    # 若無資料，給予空的 Trello 結構
    if not restya_data.get('data'):
        board_id = gen_trello_id(12345)
        empty_board = {
            "id": board_id,
            "name": "TrelloBoard",
            "desc": "",
            "closed": False,
            "idOrganization": "5b7a154eae842267f69089c4",
            "pinned": False,
            "url": "https://trello.com/b/ABCDEFGH/TrelloBoard",
            "shortLink": "ABCDEFGH",
            "shortUrl": "https://trello.com/b/ABCDEFGH",
            "subscribed": False,
            "labelNames": {
                "green": "", "yellow": "", "orange": "", "red": "", "purple": "", "blue": ""
            },
            "prefs": {
                "permissionLevel": "org",
                "hideVotes": False,
                "voting": "disabled",
                "comments": "members",
                "invitations": "members",
                "selfJoin": True,
                "cardCovers": True,
                "cardAging": "regular",
                "calendarFeedEnabled": False,
                "background": "green",
                "backgroundColor": "#519839",
                "backgroundTile": False,
                "backgroundBrightness": "dark",
                "canBePublic": True,
                "canBeEnterprise": True,
                "canBeOrg": True,
                "canBePrivate": True,
                "canInvite": True
            },
            "members": [],
            "lists": [],
            "cards": [],
            "labels": [],
            "actions": [],
            "checklists": [],
            "customFields": []
        }
        with open(output_file, "w", encoding="utf-8") as fw:
            json.dump(empty_board, fw, ensure_ascii=False, indent=2)
        print(f"轉換完成！結果已輸出至 {output_file}")
        return

    # 取得 board id (hash)
    first_list = restya_data['data'][0]
    board_id_num = first_list.get('board_id', 12345)
    board_id = gen_trello_id(board_id_num)

    # 預設組織/建立者ID，可自行調整
    id_organization = "5b7a154eae8467f69089c4"
    id_member_creator = "596d59cbd14b2ed4c5909b"

    # 用於最終輸出：board labels 容器
    board_labels_dict = {}
    
    def get_or_create_board_label(restya_label):
        """
        將 Restyaboard 的標籤物件轉成 Trello 標籤物件，若尚未建立則新增。
        :param restya_label: {'id':..., 'color': '#0091ff', ...}
        :return: Trello 格式的標籤 dict
        """
        label_id_raw = restya_label.get("id", "unknownLabel")
        color_hex = restya_label.get("color", "")

        mapped = COLOR_MAPPING.get(color_hex, {})
        trello_color = mapped.get("trello_color", "")
        label_name = mapped.get("label_name", "")

        # 若對應不到，預設 color='green', name='OK'
        if not trello_color and not label_name:
            trello_color = "green"
            label_name = "正常"

        key = (trello_color, label_name)
        if key not in board_labels_dict:
            lbl_id = gen_trello_id(label_id_raw)
            board_labels_dict[key] = {
                "id": lbl_id,
                "idBoard": board_id,
                "name": label_name,
                "color": trello_color,
                "uses": 0
            }
        return board_labels_dict[key]

    # 依 position 排序
    data_lists_sorted = sorted(
        restya_data["data"],
        key=lambda x: x.get("position", 0)
    )

    list_pos_base = 16384
    card_pos_base = 16384
    card_counter = 1

    lists = []
    cards = []
    checklists_global = []
    actions_global = []
    custom_fields_global = []

    # 開始建立清單 (lists) 與卡片 (cards)
    for li, list_item in enumerate(data_lists_sorted, start=1):
        list_id = gen_trello_id(list_item['id'])
        list_pos = list_pos_base * li

        lists.append({
            "id": list_id,
            "name": list_item.get('name', '') or "",
            "closed": (list_item.get('is_archived', 0) == 1),
            "idBoard": board_id,
            "pos": list_pos,
            "idOrganization": id_organization
        })

        # 對應卡片
        cards_data = list_item.get('cards') or []
        for ci, card_item in enumerate(cards_data, start=1):
            card_id = gen_trello_id(card_item['id'])
            cpos = list_pos + ci * card_pos_base
            desc = card_item.get('description', '') or ""
            due_value = normalize_due(card_item.get('due_date', None))

            # 處理 card 標籤 => idLabels[], labels[]
            id_labels = []
            card_labels = []
            if card_item.get("cards_labels"):
                for lb in card_item["cards_labels"]:
                    label_obj = get_or_create_board_label(lb)
                    label_obj["uses"] += 1  # 累計使用次數

                    id_labels.append(label_obj["id"])
                    card_label_copy = {
                        "id": label_obj["id"],
                        "idBoard": label_obj["idBoard"],
                        "name": label_obj["name"],
                        "color": label_obj["color"],
                        "uses": label_obj["uses"]
                    }
                    card_labels.append(card_label_copy)

            # 處理檢查清單 (checklists)
            id_checklists = []
            if card_item.get('cards_checklists'):
                for ch_i, ch in enumerate(card_item['cards_checklists'], start=1):
                    ch_id = gen_trello_id(ch['id'])
                    ch_pos = 16384 * ch_i
                    check_items = []

                    if ch.get('checklists_items'):
                        for cii, ci_item in enumerate(ch['checklists_items'], start=1):
                            ci_id = gen_trello_id(ci_item['id'])
                            state = "complete" if ci_item.get('is_completed', 0) == 1 else "incomplete"
                            check_items.append({
                                "id": ci_id,
                                "name": ci_item.get('name', ''),
                                "pos": 16384 * cii,
                                "state": state,
                                "due": None,
                                "dueReminder": None,
                                "idMember": None,
                                "idChecklist": ch_id,
                                "nameData": {"emoji": {}}
                            })

                    checklists_global.append({
                        "id": ch_id,
                        "name": ch.get('name', '') or "Checklist",
                        "idBoard": board_id,
                        "idCard": card_id,
                        "pos": ch_pos,
                        "limits": {
                            "checkItems": {
                                "perChecklist": {
                                    "status": "ok", "disableAt": 200, "warnAt": 160
                                }
                            }
                        },
                        "checkItems": check_items,
                        "creationMethod": None
                    })
                    id_checklists.append(ch_id)

            # 產生 shortLink
            card_short_link = gen_short_link(card_id)

            # 建立卡片物件 (不含成員 idMembers)
            cards.append({
                "id": card_id,
                "name": card_item.get('name', '') or "",
                "desc": desc,
                "closed": (card_item.get('is_archived', 0) == 1),
                "idBoard": board_id,
                "idList": list_id,
                "pos": cpos,
                "idShort": card_counter,
                "shortLink": card_short_link,
                "idLabels": id_labels,
                "labels": card_labels,
                "idChecklists": id_checklists,
                "due": due_value,
                "dueComplete": False,
                "dateLastActivity": datetime.datetime.utcnow().isoformat() + 'Z',
                "descData": {"emoji": {}},
                "idAttachmentCover": None,
                "idMembersVoted": [],
                "idOrganization": id_organization,
                "attachments": [],
                "subscribed": False,
                "cover": {
                    "idAttachment": None,
                    "color": None,
                    "idUploadedBackground": None,
                    "size": "normal",
                    "brightness": "dark",
                    "idPlugin": None
                },
                "manualCoverAttachment": False,
                "isTemplate": False,
                "cardRole": None,
                "creationMethod": None,
                "customFieldItems": [],
                "pluginData": []
            })
            card_counter += 1

    # 頂層 labels => boardLabelsDict
    board_labels = list(board_labels_dict.values())

    # Trello board 預設偏好設定
    prefs = {
        "permissionLevel": "org",
        "hideVotes": False,
        "voting": "disabled",
        "comments": "members",
        "invitations": "members",
        "selfJoin": True,
        "cardCovers": True,
        "cardAging": "regular",
        "calendarFeedEnabled": False,
        "background": "green",
        "backgroundColor": "#519839",
        "backgroundImage": None,
        "backgroundTile": False,
        "backgroundBrightness": "dark",
        "canBePublic": True,
        "canBeEnterprise": True,
        "canBeOrg": True,
        "canBePrivate": True,
        "canInvite": True
    }

    # 預設 memberships
    memberships = [{
        "id": gen_trello_id("boardmember"),
        "idMember": id_member_creator,
        "memberType": "admin",
        "unconfirmed": False,
        "deactivated": False
    }]

    # 各種操作數量上限
    limits = {
        "attachments": {
            "perBoard": {"status": "ok", "disableAt": 36000, "warnAt": 28800},
            "perCard": {"status": "ok", "disableAt": 1000, "warnAt": 800}
        },
        "boards": {
            "totalMembersPerBoard": {"status": "ok", "disableAt": 1600, "warnAt": 1280},
            "totalAccessRequestsPerBoard": {"status": "ok", "disableAt": 4000, "warnAt": 3200}
        },
        "cards": {
            "openPerBoard": {"status": "ok", "disableAt": 5000, "warnAt": 4000},
            "openPerList": {"status": "ok", "disableAt": 5000, "warnAt": 4000},
            "totalPerBoard": {"status": "ok", "disableAt": 2000000, "warnAt": 1600000},
            "totalPerList": {"status": "ok", "disableAt": 1000000, "warnAt": 800000}
        },
        "checklists": {
            "perBoard": {"status": "ok", "disableAt": 1800000, "warnAt": 1440000},
            "perCard": {"status": "ok", "disableAt": 500, "warnAt": 400}
        },
        "checkItems": {
            "perChecklist": {"status": "ok", "disableAt": 200, "warnAt": 160}
        },
        "customFields": {
            "perBoard": {"status": "ok", "disableAt": 50, "warnAt": 40}
        },
        "customFieldOptions": {
            "perField": {"status": "ok", "disableAt": 50, "warnAt": 40}
        },
        "labels": {
            "perBoard": {"status": "ok", "disableAt": 1000, "warnAt": 800}
        },
        "lists": {
            "openPerBoard": {"status": "ok", "disableAt": 500, "warnAt": 400},
            "totalPerBoard": {"status": "ok", "disableAt": 3000, "warnAt": 2400}
        },
        "stickers": {
            "perCard": {"status": "ok", "disableAt": 70, "warnAt": 56}
        },
        "reactions": {
            "perAction": {"status": "ok", "disableAt": 900, "warnAt": 720},
            "uniquePerAction": {"status": "ok", "disableAt": 17, "warnAt": 14}
        }
    }

    # 最終組合 Trello JSON
    trello_data = {
        "id": board_id,
        "nodeId": f"ari:cloud:trello::board/workspace/{id_organization}/{board_id}",
        "name": "RestyaBoard",  # 可自行修改看板名稱
        "desc": "",
        "descData": None,
        "closed": False,
        "dateClosed": None,
        "idOrganization": id_organization,
        "idEnterprise": None,
        "limits": limits,
        "pinned": False,
        "starred": False,
        "url": "https://trello.com/b/CJYpRTwW/xxx",
        "prefs": prefs,
        "shortLink": "CJYpRTwW",
        "subscribed": False,
        "labelNames": {
            "green": "",
            "yellow": "",
            "orange": "",
            "red": "",
            "purple": "",
            "blue": ""
        },
        "powerUps": [],
        "dateLastActivity": datetime.datetime.utcnow().isoformat() + 'Z',
        "dateLastView": datetime.datetime.utcnow().isoformat() + 'Z',
        "shortUrl": "https://trello.com/b/CJYpRTwW",
        "idTags": [],
        "datePluginDisable": None,
        "creationMethod": None,
        "ixUpdate": "63",
        "templateGallery": None,
        "enterpriseOwned": False,
        "idBoardSource": None,
        "premiumFeatures": [
            "additionalBoardBackgrounds", "additionalStickers", "customBoardBackgrounds",
            "customEmoji", "customStickers", "plugins"
        ],
        "idMemberCreator": id_member_creator,
        "type": None,
        "actions": actions_global,
        "cards": cards,
        "labels": board_labels,
        "lists": lists,
        "members": [],
        "checklists": checklists_global,
        "customFields": custom_fields_global,
        "memberships": memberships,
        "pluginData": []
    }

    # 寫出最終結果
    with open(output_file, "w", encoding="utf-8") as fw:
        json.dump(trello_data, fw, ensure_ascii=False, indent=2)

    print(f"轉換完成！結果已輸出至 {output_file}")

if __name__ == "__main__":
    main()


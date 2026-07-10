"""
A2UI v0.8 Card Templates & Helper Generators for AppSheet Data Presentation.

Gemini Enterprise strictly requires A2UI version v0.8 layout structures.

AI ASSISTANT GUIDE FOR CUSTOM CARDS:
------------------------------------
1. Structure: A2UI v0.8 layouts are lists of command dictionaries:
   [ {"beginRendering": {...}}, {"surfaceUpdate": {...}} ]
2. DataPart wrapping: In your AgentExecutor, wrap EACH command dictionary in its own DataPart:
   Part(root=DataPart(data=cmd, metadata={"mimeType": "application/json+a2ui"}))
3. Customizing Columns: Modify `create_record_card` or `create_table_list_card` below
   to map your AppSheet table columns to Text or Card components.
"""

from typing import List, Dict, Any

def create_record_card(surface_id: str, title: str, record_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generates an A2UI v0.8 layout array displaying a single AppSheet record's key-value fields.

    Args:
        surface_id (str): Unique surface ID for the card (e.g. "record-detail-card").
        title (str): Header title for the card.
        record_data (Dict[str, Any]): Dictionary of column names and values from AppSheet.

    Returns:
        List[Dict[str, Any]]: A2UI v0.8 command array.
    """
    components = []
    
    # 1. Root Card component
    components.append({
        "id": "root_card",
        "component": {
            "Card": {
                "child": "main_column"
            }
        }
    })

    # 2. Main Column component holding title + rows
    child_ids = ["title_text"]
    
    # Generate Text components for each field
    field_components = []
    for idx, (key, value) in enumerate(record_data.items()):
        field_id = f"field_{idx}"
        child_ids.append(field_id)
        field_components.append({
            "id": field_id,
            "component": {
                "Text": {
                    "text": {
                        "literalString": f"• {key}: {value}"
                    },
                    "usageHint": "body"
                }
            }
        })

    components.append({
        "id": "main_column",
        "component": {
            "Column": {
                "children": {
                    "explicitList": child_ids
                }
            }
        }
    })

    # Title Text component
    components.append({
        "id": "title_text",
        "component": {
            "Text": {
                "text": {
                    "literalString": title
                },
                "usageHint": "h3"
            }
        }
    })

    # Add all field text components
    components.extend(field_components)

    return [
        {
            "beginRendering": {
                "surfaceId": surface_id,
                "root": "root_card"
            }
        },
        {
            "surfaceUpdate": {
                "surfaceId": surface_id,
                "components": components
            }
        }
    ]


def create_status_card(surface_id: str, title: str, message: str, success: bool = True) -> List[Dict[str, Any]]:
    """
    Generates a simple status/notification A2UI v0.8 card (e.g., action feedback).
    """
    status_icon = "✅" if success else "❌"
    return [
        {
            "beginRendering": {
                "surfaceId": surface_id,
                "root": "status_card"
            }
        },
        {
            "surfaceUpdate": {
                "surfaceId": surface_id,
                "components": [
                    {
                        "id": "status_card",
                        "component": {
                            "Card": {
                                "child": "status_col"
                            }
                        }
                    },
                    {
                        "id": "status_col",
                        "component": {
                            "Column": {
                                "children": {
                                    "explicitList": ["status_title", "status_msg"]
                                }
                            }
                        }
                    },
                    {
                        "id": "status_title",
                        "component": {
                            "Text": {
                                "text": {
                                    "literalString": f"{status_icon} {title}"
                                },
                                "usageHint": "h3"
                            }
                        }
                    },
                    {
                        "id": "status_msg",
                        "component": {
                            "Text": {
                                "text": {
                                    "literalString": message
                                },
                                "usageHint": "body"
                            }
                        }
                    }
                ]
            }
        }
    ]


def create_table_list_card(surface_id: str, title: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generates an A2UI v0.8 layout displaying a list of records as a vertical set of cards.
    """
    if not records:
        return create_status_card(surface_id, title, "No records to display", success=False)
        
    components = []
    
    # 1. Root Card component
    components.append({
        "id": "root_card",
        "component": {
            "Card": {
                "child": "main_column"
            }
        }
    })
    
    # 2. Main Column holding Title, Divider, and Record Cards
    child_ids = ["title_text", "header_divider"]
    
    # Limit to top 8 records to keep the A2UI surface payload token-efficient and responsive
    display_records = records[:8]
    
    item_components = []
    for idx, rec in enumerate(display_records):
        card_id = f"item_card_{idx}"
        col_id = f"item_col_{idx}"
        child_ids.append(card_id)
        
        # Build contents inside the record item card
        item_fields = list(rec.items())
        # First field is the title/header
        title_key, title_val = item_fields[0] if len(item_fields) > 0 else ("ID", f"Item {idx}")
        
        rec_child_ids = [f"item_title_{idx}"]
        
        # Header component inside item card
        item_components.append({
            "id": f"item_title_{idx}",
            "component": {
                "Text": {
                    "text": {
                        "literalString": f"• {title_key}: {title_val}"
                    },
                    "usageHint": "h3"
                }
            }
        })
        
        # Add up to 3 additional subtitle/detail fields
        for f_idx, (key, value) in enumerate(item_fields[1:4]):
            field_id = f"item_detail_{idx}_{f_idx}"
            rec_child_ids.append(field_id)
            item_components.append({
                "id": field_id,
                "component": {
                    "Text": {
                        "text": {
                            "literalString": f"  {key}: {value}"
                        },
                        "usageHint": "caption"
                    }
                }
            })
            
        # Add the item card and its column container
        item_components.append({
            "id": card_id,
            "component": {
                "Card": {
                    "child": col_id
                }
            }
        })
        
        item_components.append({
            "id": col_id,
            "component": {
                "Column": {
                    "children": {
                        "explicitList": rec_child_ids
                    }
                }
            }
        })
        
    components.append({
        "id": "main_column",
        "component": {
            "Column": {
                "children": {
                    "explicitList": child_ids
                },
                "alignment": "stretch"
            }
        }
    })
    
    # Title Text component
    components.append({
        "id": "title_text",
        "component": {
            "Text": {
                "text": {
                    "literalString": title
                },
                "usageHint": "h2"
            }
        }
    })
    
    # Divider
    components.append({
        "id": "header_divider",
        "component": {
            "Divider": {
                "axis": "horizontal"
            }
        }
    })
    
    # Add all generated item components
    components.extend(item_components)
    
    return [
        {
            "beginRendering": {
                "surfaceId": surface_id,
                "root": "root_card"
            }
        },
        {
            "surfaceUpdate": {
                "surfaceId": surface_id,
                "components": components
            }
        }
    ]


def create_form_card(surface_id: str, title: str, columns: Dict[str, Any], submit_action: str) -> List[Dict[str, Any]]:
    """
    Generates an A2UI v0.8 input form layout dynamically mapping AppSheet schemas to v0.8 input elements.
    """
    components = []
    
    # 1. Root Card component
    components.append({
        "id": "root_card",
        "component": {
            "Card": {
                "child": "main_column"
            }
        }
    })
    
    # 2. Main Column holding form elements
    child_ids = ["form_title", "header_divider"]
    
    form_components = []
    data_contents = []
    
    # Track the value paths for submission mapping
    context_bindings = []
    
    for idx, (col_name, col_meta) in enumerate(columns.items()):
        col_lower = col_name.lower()
        if col_lower in ("id", "key") or col_lower.endswith("_computedname") or col_lower.endswith("timestamp"):
            continue
            
        field_id = f"field_{idx}"
        label_id = f"label_{idx}"
        
        col_type = col_meta.get("type", "string")
        required = col_meta.get("required", False)
        label_str = f"{col_name}*" if required else col_name
        
        path_name = f"/form/{col_name.replace(' ', '_')}"
        
        # Check compatibility matrix mappings
        if col_type == "boolean":
            # Map Yes/No to CheckBox
            form_components.append({
                "id": field_id,
                "component": {
                    "CheckBox": {
                        "label": {
                            "literalString": label_str
                        },
                        "value": {
                            "path": path_name
                        }
                    }
                }
            })
            child_ids.append(field_id)
            data_contents.append({
                "key": path_name.strip("/"),
                "valueBoolean": False
            })
            context_bindings.append({
                "key": col_name,
                "value": {
                    "path": path_name
                }
            })
        elif col_type in ("date", "time", "datetime"):
            # Map Dates to DateTimeInput
            form_components.append({
                "id": field_id,
                "component": {
                    "DateTimeInput": {
                        "label": {
                            "literalString": label_str
                        },
                        "value": {
                            "path": path_name
                        },
                        "enableDate": col_type in ("date", "datetime"),
                        "enableTime": col_type in ("time", "datetime")
                    }
                }
            })
            child_ids.append(field_id)
            data_contents.append({
                "key": path_name.strip("/"),
                "valueString": ""
            })
            context_bindings.append({
                "key": col_name,
                "value": {
                    "path": path_name
                }
            })
        elif col_meta.get("enum"):
            # Map Enum to MultipleChoice
            options = []
            for opt in col_meta.get("enum", []):
                options.append({
                    "label": {
                        "literalString": str(opt)
                    },
                    "value": str(opt)
                })
            form_components.append({
                "id": label_id,
                "component": {
                    "Text": {
                        "text": {
                            "literalString": label_str
                        },
                        "usageHint": "caption"
                    }
                }
            })
            form_components.append({
                "id": field_id,
                "component": {
                    "MultipleChoice": {
                        "options": options,
                        "selections": {
                            "path": path_name
                        },
                        "maxAllowedSelections": 1
                    }
                }
            })
            child_ids.extend([label_id, field_id])
            data_contents.append({
                "key": path_name.strip("/"),
                "valueString": ""
            })
            context_bindings.append({
                "key": col_name,
                "value": {
                    "path": path_name
                }
            })
        else:
            # Fallback to TextField
            text_field_type = "shortText"
            if col_type == "integer" or col_type == "number":
                text_field_type = "number"
            elif col_lower.endswith("description") or col_lower.endswith("notes"):
                text_field_type = "longText"
                
            form_components.append({
                "id": field_id,
                "component": {
                    "TextField": {
                        "label": {
                            "literalString": label_str
                        },
                        "text": {
                            "path": path_name
                        },
                        "textFieldType": text_field_type
                    }
                }
            })
            child_ids.append(field_id)
            data_contents.append({
                "key": path_name.strip("/"),
                "valueString": ""
            })
            context_bindings.append({
                "key": col_name,
                "value": {
                    "path": path_name
                }
            })
            
    # Add Submit Button
    submit_btn_text_id = "btn_submit_text"
    submit_btn_id = "btn_submit"
    child_ids.append(submit_btn_id)
    
    form_components.append({
        "id": submit_btn_text_id,
        "component": {
            "Text": {
                "text": {
                    "literalString": "Submit"
                }
            }
        }
    })
    
    form_components.append({
        "id": submit_btn_id,
        "component": {
            "Button": {
                "child": submit_btn_text_id,
                "primary": True,
                "action": {
                    "name": submit_action,
                    "context": context_bindings
                }
            }
        }
    })
    
    components.append({
        "id": "main_column",
        "component": {
            "Column": {
                "children": {
                    "explicitList": child_ids
                },
                "alignment": "stretch"
            }
        }
    })
    
    # Title Text component
    components.append({
        "id": "form_title",
        "component": {
            "Text": {
                "text": {
                    "literalString": title
                },
                "usageHint": "h2"
            }
        }
    })
    
    # Divider
    components.append({
        "id": "header_divider",
        "component": {
            "Divider": {
                "axis": "horizontal"
            }
        }
    })
    
    # Add all form input elements
    components.extend(form_components)
    
    return [
        {
            "beginRendering": {
                "surfaceId": surface_id,
                "root": "root_card"
            }
        },
        {
            "surfaceUpdate": {
                "surfaceId": surface_id,
                "components": components
            }
        },
        {
            "dataModelUpdate": {
                "surfaceId": surface_id,
                "path": "/",
                "contents": data_contents
            }
        }
    ]



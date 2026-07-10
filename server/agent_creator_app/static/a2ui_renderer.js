/**
 * A2UI v0.8 Client Web Renderer.
 * Interprets A2UI command arrays (beginRendering, surfaceUpdate) and constructs HTML DOM elements.
 * Renders true interactive HTML form controls (<input>, <button>) and structured layouts (Columns, Container, Table)
 * for live testing in Section 3.
 * Stylized in AppSheet Enterprise Light theme.
 */
class A2UIRenderer {
    static renderCommands(commands) {
        const container = document.createElement('div');
        container.className = 'a2ui-card-container';

        let componentsMap = {};
        let rootKey = null;

        // Parse commands
        commands.forEach(cmd => {
            if (cmd.beginRendering && cmd.beginRendering.root) {
                rootKey = cmd.beginRendering.root;
            }
            if (cmd.surfaceUpdate && cmd.surfaceUpdate.components) {
                cmd.surfaceUpdate.components.forEach(comp => {
                    componentsMap[comp.id] = comp.component;
                });
            }
        });

        // Use the explicit root key if found and mapped
        if (rootKey && componentsMap[rootKey]) {
            const el = this._renderComponent(componentsMap[rootKey], componentsMap);
            container.appendChild(el);
        } else {
            // Fallback: render keys ending in _card or form_card / detail_card
            const rootKeys = Object.keys(componentsMap).filter(k => k.endsWith('_card') || k === 'root_card' || k === 'form_card' || k === 'detail_card' || k.endsWith('_card_root') || k.endsWith('_root_column'));
            
            if (rootKeys.length > 0) {
                rootKeys.forEach(key => {
                    const el = this._renderComponent(componentsMap[key], componentsMap);
                    container.appendChild(el);
                });
            } else {
                const firstComp = Object.values(componentsMap)[0];
                if (firstComp) {
                    container.appendChild(this._renderComponent(firstComp, componentsMap));
                } else {
                    container.innerText = "Empty A2UI Surface Payload";
                }
            }
        }

        return container;
    }

    static _renderComponent(compObj, map) {
        if (!compObj) return document.createElement('div');

        if (compObj.Card) {
            const cardEl = document.createElement('div');
            cardEl.className = 'a2ui-card';
            cardEl.style.background = '#ffffff';
            cardEl.style.border = '1px solid #cbd5e1';
            cardEl.style.borderRadius = '8px';
            cardEl.style.padding = '14px';
            cardEl.style.margin = '8px 0';
            cardEl.style.boxShadow = '0 1px 3px rgba(0,0,0,0.05)';

            if (compObj.Card.child && map[compObj.Card.child]) {
                cardEl.appendChild(this._renderComponent(map[compObj.Card.child], map));
            }
            return cardEl;
        }

        if (compObj.Column) {
            const colEl = document.createElement('div');
            colEl.className = 'a2ui-column';
            colEl.style.display = 'flex';
            colEl.style.flexDirection = 'column';
            colEl.style.gap = '8px';

            let childrenIds = [];
            if (Array.isArray(compObj.Column.children)) {
                childrenIds = compObj.Column.children;
            } else if (compObj.Column.children && Array.isArray(compObj.Column.children.explicitList)) {
                childrenIds = compObj.Column.children.explicitList;
            }

            childrenIds.forEach(child => {
                if (typeof child === 'string') {
                    if (map[child]) {
                        colEl.appendChild(this._renderComponent(map[child], map));
                    }
                } else if (child && typeof child === 'object') {
                    if (child.id && map[child.id]) {
                        colEl.appendChild(this._renderComponent(map[child.id], map));
                    } else if (child.component) {
                        colEl.appendChild(this._renderComponent(child.component, map));
                    } else {
                        colEl.appendChild(this._renderComponent(child, map));
                    }
                }
            });
            return colEl;
        }

        if (compObj.Container) {
            const containerEl = document.createElement('div');
            containerEl.className = 'a2ui-container';
            containerEl.style.display = 'flex';
            const dir = compObj.Container.direction || "VERTICAL";
            containerEl.style.flexDirection = dir === "HORIZONTAL" ? "row" : "column";
            containerEl.style.gap = compObj.Container.spacing === "EXTRA_SMALL" ? "4px" : (compObj.Container.spacing === "MEDIUM" ? "12px" : "8px");
            containerEl.style.margin = '4px 0';
            
            let children = [];
            if (Array.isArray(compObj.Container.children)) {
                children = compObj.Container.children;
            } else if (compObj.Container.children && Array.isArray(compObj.Container.children.explicitList)) {
                children = compObj.Container.children.explicitList;
            }
            
            children.forEach(child => {
                if (typeof child === 'string') {
                    if (map[child]) {
                        containerEl.appendChild(this._renderComponent(map[child], map));
                    }
                } else if (child && typeof child === 'object') {
                    if (child.id && map[child.id]) {
                        containerEl.appendChild(this._renderComponent(map[child.id], map));
                    } else if (child.component) {
                        containerEl.appendChild(this._renderComponent(child.component, map));
                    } else {
                        containerEl.appendChild(this._renderComponent(child, map));
                    }
                }
            });
            return containerEl;
        }

        if (compObj.ColumnSet) {
            const rowEl = document.createElement('div');
            rowEl.className = 'a2ui-column-set';
            rowEl.style.display = 'flex';
            rowEl.style.flexDirection = 'row';
            rowEl.style.width = '100%';
            rowEl.style.gap = '10px';
            rowEl.style.margin = '4px 0';
            
            const cols = compObj.ColumnSet.columns || [];
            cols.forEach(col => {
                const colEl = document.createElement('div');
                colEl.className = 'a2ui-column-set-col';
                colEl.style.flex = '1';
                colEl.style.display = 'flex';
                colEl.style.flexDirection = 'column';
                colEl.style.gap = '6px';
                
                const colComponents = col.components || [];
                colComponents.forEach(child => {
                    if (typeof child === 'string') {
                        if (map[child]) {
                            colEl.appendChild(this._renderComponent(map[child], map));
                        }
                    } else if (child && typeof child === 'object') {
                        if (child.id && map[child.id]) {
                            colEl.appendChild(this._renderComponent(map[child.id], map));
                        } else if (child.component) {
                            colEl.appendChild(this._renderComponent(child.component, map));
                        } else {
                            colEl.appendChild(this._renderComponent(child, map));
                        }
                    }
                });
                rowEl.appendChild(colEl);
            });
            return rowEl;
        }

        if (compObj.Table) {
            const tableWrapper = document.createElement('div');
            tableWrapper.style.overflowX = 'auto';
            tableWrapper.style.margin = '8px 0';
            tableWrapper.style.border = '1px solid #cbd5e1';
            tableWrapper.style.borderRadius = '6px';
            tableWrapper.style.width = '100%';
            
            const table = document.createElement('table');
            table.style.width = '100%';
            table.style.borderCollapse = 'collapse';
            table.style.fontSize = '0.8rem';
            
            const thead = document.createElement('thead');
            thead.style.background = '#f8fafc';
            thead.style.borderBottom = '1px solid #cbd5e1';
            const headerRow = document.createElement('tr');
            
            const cols = compObj.Table.columns || [];
            cols.forEach(col => {
                const th = document.createElement('th');
                th.innerText = col.title || "Column";
                th.style.padding = '8px';
                th.style.textAlign = 'left';
                th.style.fontWeight = '600';
                th.style.color = '#475569';
                headerRow.appendChild(th);
            });
            thead.appendChild(headerRow);
            table.appendChild(thead);
            
            const tbody = document.createElement('tbody');
            const mockRows = [
                {"Name": "John Doe", "Email": "john.doe@example.com", "Phone": "555-123-4567"},
                {"Name": "Jane Smith", "Email": "jane.smith@example.com", "Phone": "555-987-6543"}
            ];
            
            mockRows.forEach((row, rIdx) => {
                const tr = document.createElement('tr');
                tr.style.borderBottom = rIdx < mockRows.length - 1 ? '1px solid #e2e8f0' : 'none';
                
                cols.forEach(col => {
                    const td = document.createElement('td');
                    const key = col.dataBinding || col.key || "Name";
                    td.innerText = row[key] || "N/A";
                    td.style.padding = '8px';
                    td.style.color = '#1e293b';
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            tableWrapper.appendChild(table);
            return tableWrapper;
        }

        if (compObj.Text) {
            const str = compObj.Text.text?.literalString || "";
            const hint = compObj.Text.usageHint || compObj.Text.typography || "body";

            // Check if this text node contains a form field placeholder
            if (str.includes("[ Form Input Component ]")) {
                const fieldBox = document.createElement('div');
                fieldBox.style.display = 'flex';
                fieldBox.style.flexDirection = 'column';
                fieldBox.style.gap = '4px';

                const labelText = str.replace("[ Form Input Component ]", "").trim();
                const label = document.createElement('label');
                label.innerText = labelText;
                label.style.fontSize = '0.8rem';
                label.style.fontWeight = '600';
                label.style.color = '#475569';

                const input = document.createElement('input');
                input.type = 'text';
                input.className = 'a2ui-input';
                input.placeholder = `Enter ${labelText.replace('•', '').replace('(Required)', '').trim()}...`;
                input.style.padding = '6px 10px';
                input.style.borderRadius = '4px';
                input.style.border = '1px solid #cbd5e1';
                input.style.background = '#ffffff';
                input.style.color = '#1e293b';
                input.style.fontSize = '0.8rem';

                fieldBox.appendChild(label);
                fieldBox.appendChild(input);
                return fieldBox;
            }

            // Check if this text node contains a boolean checkbox placeholder
            if (str.includes("[ Checkbox Component ]")) {
                const checkLabel = document.createElement('label');
                checkLabel.style.display = 'flex';
                checkLabel.style.alignItems = 'center';
                checkLabel.style.gap = '8px';
                checkLabel.style.cursor = 'pointer';
                checkLabel.style.fontSize = '0.8rem';
                checkLabel.style.color = '#1e293b';
                checkLabel.style.margin = '4px 0';
                checkLabel.style.fontWeight = '500';

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.style.cursor = 'pointer';
                checkbox.style.width = '14px';
                checkbox.style.height = '14px';

                const cleanText = str.replace("[ Checkbox Component ]", "").replace('•', '').trim();
                const textSpan = document.createElement('span');
                textSpan.innerText = cleanText;

                checkLabel.appendChild(checkbox);
                checkLabel.appendChild(textSpan);
                return checkLabel;
            }

            const textEl = document.createElement('div');
            textEl.className = `a2ui-${hint}`;
            if (hint === 'h3' || hint === 'displaySmall' || hint === 'title' || hint === 'HEADING_4') {
                textEl.style.fontWeight = '600';
                textEl.style.fontSize = '0.95rem';
                textEl.style.color = '#1a73e8';
                textEl.style.marginBottom = '4px';
            } else {
                textEl.style.fontSize = '0.8rem';
                textEl.style.color = '#475569';
            }
            textEl.innerText = str;
            return textEl;
        }

        // Native A2UI Gallery Component: TextField
        if (compObj.TextField) {
            const fieldBox = document.createElement('div');
            fieldBox.style.display = 'flex';
            fieldBox.style.flexDirection = 'column';
            fieldBox.style.gap = '4px';

            const labelVal = compObj.TextField.label?.literalString || "Text Field";
            const label = document.createElement('label');
            label.innerText = labelVal;
            label.style.fontSize = '0.8rem';
            label.style.fontWeight = '600';
            label.style.color = '#475569';

            const type = compObj.TextField.textFieldType || "shortText";
            const input = type === "longText" ? document.createElement('textarea') : document.createElement('input');
            
            if (type !== "longText") {
                input.type = type === "obscured" ? "password" : (type === "number" ? "number" : (type === "date" ? "date" : "text"));
            }
            
            input.className = 'a2ui-input';
            input.style.padding = '6px 10px';
            input.style.borderRadius = '4px';
            input.style.border = '1px solid #cbd5e1';
            input.style.background = '#ffffff';
            input.style.color = '#1e293b';
            input.style.fontSize = '0.8rem';
            if (type === "longText") {
                input.style.height = '50px';
                input.style.resize = 'vertical';
            }

            fieldBox.appendChild(label);
            fieldBox.appendChild(input);
            return fieldBox;
        }

        // Native A2UI Gallery Component: CheckBox
        if (compObj.CheckBox) {
            const checkLabel = document.createElement('label');
            checkLabel.style.display = 'flex';
            checkLabel.style.alignItems = 'center';
            checkLabel.style.gap = '8px';
            checkLabel.style.cursor = 'pointer';
            checkLabel.style.fontSize = '0.8rem';
            checkLabel.style.color = '#1e293b';
            checkLabel.style.margin = '4px 0';
            checkLabel.style.fontWeight = '500';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.style.cursor = 'pointer';
            checkbox.style.width = '14px';
            checkbox.style.height = '14px';
            
            const isChecked = compObj.CheckBox.value?.literalBoolean || false;
            checkbox.checked = isChecked;

            const labelVal = compObj.CheckBox.label?.literalString || "Checkbox";
            const textSpan = document.createElement('span');
            textSpan.innerText = labelVal;

            checkLabel.appendChild(checkbox);
            checkLabel.appendChild(textSpan);
            return checkLabel;
        }

        // Native A2UI Gallery Component: Button
        if (compObj.Button) {
            const btn = document.createElement('button');
            const isPrimary = compObj.Button.primary || false;
            btn.className = isPrimary ? 'btn btn-primary' : 'btn btn-secondary';
            btn.style.marginTop = '8px';
            btn.style.padding = '6px 12px';
            btn.style.fontSize = '0.8rem';
            btn.style.borderRadius = '4px';

            let btnLabel = "Button";
            if (compObj.Button.child && map[compObj.Button.child]) {
                const childObj = map[compObj.Button.child];
                btnLabel = childObj.Text?.text?.literalString || btnLabel;
            } else if (compObj.Button.label?.literalString) {
                btnLabel = compObj.Button.label.literalString;
            }
            btn.innerText = btnLabel;

            btn.addEventListener('click', () => {
                const actionName = compObj.Button.action?.name || "unspecified";
                alert(`✨ A2UI v0.8 Button Clicked!\n\nAction Target: '${actionName}'\nLabel: '${btnLabel}'`);
            });
            return btn;
        }

        // Native A2UI Gallery Component: Divider
        if (compObj.Divider) {
            const axis = compObj.Divider.axis || "horizontal";
            const el = document.createElement('hr');
            el.style.border = '0';
            if (axis === "horizontal") {
                el.style.borderTop = '1px solid #e2e8f0';
                el.style.margin = '10px 0';
            } else {
                el.style.borderLeft = '1px solid #e2e8f0';
                el.style.height = '100%';
                el.style.margin = '0 10px';
                el.style.display = 'inline-block';
            }
            return el;
        }

        const fallback = document.createElement('div');
        fallback.innerText = JSON.stringify(compObj);
        return fallback;
    }
}

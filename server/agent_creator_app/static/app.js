// Global JWT Decoder for Google Identity Services
function parseJwt(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(jsonPayload);
    } catch (e) {
        console.error("[AppSheet Creator Studio] JWT Decode error:", e);
        return null;
    }
}

// Convert Hex Zip String to Binary Blob and Trigger Browser Download
function hexToBlob(hexString, mimeType = "application/zip") {
    const bytes = new Uint8Array(hexString.match(/.{1,2}/g).map(byte => parseInt(byte, 16)));
    return new Blob([bytes], { type: mimeType });
}

function triggerZipDownload(hexString, filename) {
    const blob = hexToBlob(hexString);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

// Global Progress Overlay Controls
function showLoading(title, subtitle) {
    const overlay = document.getElementById("loading-overlay");
    const titleEl = document.getElementById("loading-title");
    const subEl = document.getElementById("loading-subtitle");

    if (titleEl) titleEl.innerText = title || "Processing Request...";
    if (subEl) subEl.innerText = subtitle || "Please wait while AppSheet Agent Creator prepares your data.";
    if (overlay) overlay.classList.remove("hidden");
}

function hideLoading() {
    const overlay = document.getElementById("loading-overlay");
    if (overlay) overlay.classList.add("hidden");
}

// Lightweight Markdown to HTML Formatter for Section 3 Chat Bubbles
function formatMarkdown(text) {
    if (!text) return "";
    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");

    // Bold formatting: **text**
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Code formatting: `code`
    html = html.replace(/`(.*?)`/g, "<code style='background: rgba(15, 23, 42, 0.6); padding: 2px 6px; border-radius: 4px; color: #38bdf8; font-family: monospace; font-size: 0.85em;'>$1</code>");

    // Process line-by-line to handle bullet lists cleanly without double spacing
    const lines = html.split("\n");
    const processedLines = lines.map(line => {
        const trimmed = line.trim();
        if (trimmed.startsWith("•") || trimmed.startsWith("*") || trimmed.startsWith("-")) {
            const content = trimmed.substring(1).trim();
            return `<li style='margin-left: 16px; margin-top: 4px; margin-bottom: 4px;'>${content}</li>`;
        }
        return line;
    });

    let finalHtml = "";
    for (let i = 0; i < processedLines.length; i++) {
        const line = processedLines[i];
        finalHtml += line;
        // Only add line breaks if the current line does not end a list item
        if (i < processedLines.length - 1 && !line.endsWith("</li>")) {
            finalHtml += "<br>";
        }
    }

    return finalHtml;
}

// Global Callback triggered by Google Sign-In button
window.handleCredentialResponse = function(response) {
    console.log("[AppSheet Creator Studio] Google OAuth Response received");
    if (response && response.credential) {
        const payload = parseJwt(response.credential);
        if (payload && payload.email) {
            console.log("[AppSheet Creator Studio] Authenticated user:", payload.email);
            const emailInput = document.getElementById("dev-email-input");
            const badge = document.getElementById("user-email-badge");
            
            emailInput.value = payload.email;
            badge.innerText = `Logged in as: ${payload.email} (Google OAuth)`;
            badge.style.background = "rgba(34, 197, 94, 0.2)";
            badge.style.color = "#4ade80";

            if (window.fetchSavedAgents) {
                window.fetchSavedAgents();
            }
        }
    }
};

document.addEventListener("DOMContentLoaded", () => {
    console.log("[AppSheet Creator Studio] Initializing Studio UI...");

    const uploadForm = document.getElementById("upload-form");
    const openapiInput = document.getElementById("openapi-file");
    const docInput = document.getElementById("doc-file");
    const parseStatus = document.getElementById("parse-status");
    
    const appIdInput = document.getElementById("app-id");
    const accessKeyInput = document.getElementById("access-key");
    const regionSelect = document.getElementById("region");
    const serviceUrlInput = document.getElementById("service-url");
    const vertexModeCheckbox = document.getElementById("vertex-mode");
    const gcpProjectBox = document.getElementById("gcp-project-box");
    const gcpProjectInput = document.getElementById("gcp-project");

    const generateBtn = document.getElementById("generate-btn");
    const downloadZipBtn = document.getElementById("download-zip-btn");
    const showDeployGuideBtn = document.getElementById("show-deploy-guide-btn");
    const deployGuideBox = document.getElementById("deploy-guide-box");
    const deployCommandsOutput = document.getElementById("deploy-commands-output");
    const copyDeployScriptBtn = document.getElementById("copy-deploy-script-btn");
    
    const devEmailInput = document.getElementById("dev-email-input");
    const userEmailBadge = document.getElementById("user-email-badge");
    const savedAgentsSelect = document.getElementById("saved-agents-select");
    const refreshAgentsBtn = document.getElementById("refresh-agents-btn");
    const saveMgmtBtn = document.getElementById("save-mgmt-btn");

    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("send-btn");
    const chatMessages = document.getElementById("chat-messages");
    const downloadChatBtn = document.getElementById("download-chat-btn");
    const jsonOutput = document.getElementById("json-output");
    const copyBtn = document.getElementById("copy-btn");

    let parsedAppData = null;
    let savedAgentsList = [];
    let conversationHistory = [];
    let activeTables = {};
    let activeCapabilities = [];
    let latestZipBase64 = null;
    let latestRegistrationJson = null;

    try {
        const stored = localStorage.getItem("appsheet_active_tables");
        if (stored) activeTables = JSON.parse(stored);
        console.log("[AppSheet Creator Studio] Loaded active tables from localStorage:", Object.keys(activeTables));
    } catch (e) {}

    function getCurrentUserEmail() {
        return devEmailInput.value.trim() || "";
    }

    function updateBadge(email) {
        if (email) {
            userEmailBadge.innerText = `User Email: ${email}`;
        } else {
            userEmailBadge.innerText = `Not logged in`;
        }
    }

    devEmailInput.addEventListener("input", () => {
        const email = getCurrentUserEmail();
        console.log("[AppSheet Creator Studio] Dev email input changed:", email);
        updateBadge(email);
        fetchSavedAgents();
    });

    vertexModeCheckbox.addEventListener("change", () => {
        if (vertexModeCheckbox.checked) {
            gcpProjectBox.classList.remove("hidden");
        } else {
            gcpProjectBox.classList.add("hidden");
        }
    });

    function buildCustomizedDeploymentScript(appId, accessKey, region, serviceUrl) {
        const serviceName = `appsheet-agent-${appId.slice(0, 8)}`;
        return `# ------------------------------------------------------------------------------
# APPSHEET AGENT GOOGLE CLOUD RUN DEPLOYMENT SCRIPT
# App ID: ${appId}
# Target Service URL: ${serviceUrl}
# ------------------------------------------------------------------------------

# 1. Unzip downloaded agent package
unzip appsheet_agent_package_${appId}.zip -d ${serviceName}
cd ${serviceName}

# 2. Deploy to Google Cloud Run with AppSheet API Credentials & RunAsUserEmail
gcloud run deploy ${serviceName} \\
  --source . \\
  --region europe-west1 \\
  --allow-unauthenticated \\
  --set-env-vars APPSHEET_APP_ID="${appId}",APPSHEET_ACCESS_KEY="${accessKey}",APPSHEET_REGION="${region}"

# 3. Next Step: Copy the Gemini Enterprise Admin Registration JSON below
# and paste it into Gemini Enterprise Admin -> Agents -> Add Custom Agent!`;
    }

    // 1. Fetch User's Saved Agents from AppSheet Management App
    window.fetchSavedAgents = async function(selectAppIdAfterFetch) {
        const email = getCurrentUserEmail();
        if (!email) {
            savedAgentsSelect.innerHTML = '<option value="">-- Enter Email or Log In First --</option>';
            return;
        }

        console.log("[AppSheet Creator Studio] Querying Management App for user:", email);
        showLoading("Loading Saved Agents...", `Querying AppSheet Management App for '${email}'...`);
        try {
            const resp = await fetch(`/api/management/agents?user_email=${encodeURIComponent(email)}`);
            const data = await resp.json();
            console.log("[AppSheet Creator Studio] Management App Agents response:", data);

            savedAgentsSelect.innerHTML = '<option value="">-- Select Saved Agent --</option>';
            if (data.agents && data.agents.length > 0) {
                savedAgentsList = data.agents;
                data.agents.forEach(agent => {
                    const opt = document.createElement("option");
                    opt.value = agent.app_id;
                    opt.innerText = `App ID: ${agent.app_id} (${agent.status || 'Draft'})`;
                    savedAgentsSelect.appendChild(opt);
                });

                if (selectAppIdAfterFetch) {
                    savedAgentsSelect.value = selectAppIdAfterFetch;
                }
            } else {
                savedAgentsSelect.innerHTML = '<option value="">-- No Saved Agents Found for User --</option>';
            }
        } catch (err) {
            console.error("[AppSheet Creator Studio] Failed to load management agents:", err);
        } finally {
            hideLoading();
        }
    };

    refreshAgentsBtn.addEventListener("click", () => window.fetchSavedAgents());

    if (getCurrentUserEmail()) {
        updateBadge(getCurrentUserEmail());
        window.fetchSavedAgents();
    }

    appIdInput.addEventListener("input", () => {
        if (savedAgentsSelect.value !== appIdInput.value.trim()) {
            savedAgentsSelect.value = "";
        }
    });

    // 2. Select Saved Agent from Management App & Load Session
    savedAgentsSelect.addEventListener("change", async () => {
        const selectedAppId = savedAgentsSelect.value;
        if (!selectedAppId) return;

        const email = getCurrentUserEmail();
        console.log("[AppSheet Creator Studio] Loading agent session for App ID:", selectedAppId);
        showLoading("Loading Agent Session...", `Decoding openapi.json & table schemas for '${selectedAppId}'...`);

        const formData = new FormData();
        formData.append("app_id", selectedAppId);
        formData.append("user_email", email);

        try {
            const resp = await fetch("/api/management/load_agent_session", {
                method: "POST",
                body: formData
            });

            const data = await resp.json();
            console.log("[AppSheet Creator Studio] Agent session loaded response:", data);
            if (!resp.ok) throw new Error(data.detail);

            appIdInput.value = data.app_id || selectedAppId;
            if (data.appsheet_key) accessKeyInput.value = data.appsheet_key;
            if (data.deployed_url) serviceUrlInput.value = data.deployed_url;

            activeTables = data.table_details || {};
            activeCapabilities = [];
            localStorage.setItem("appsheet_active_tables", JSON.stringify(activeTables));

            const tablesCount = Object.keys(activeTables).length;
            if (parseStatus) {
                if (tablesCount === 0) {
                    parseStatus.style.background = "rgba(239, 68, 68, 0.15)";
                    parseStatus.style.color = "#f87171";
                    parseStatus.innerText = "⚠️ No tables detected. Please upload your app's openapi.json file below to start designing your agent.";
                    parseStatus.classList.remove("hidden");
                } else {
                    parseStatus.style.background = "rgba(56, 189, 248, 0.15)";
                    parseStatus.style.color = "#38bdf8";
                    parseStatus.innerText = `✅ Loaded agent session! Detected ${tablesCount} tables.`;
                    parseStatus.classList.remove("hidden");
                }
            }

            // Reset progressive disclosure states
            generateBtn.disabled = true;
            document.getElementById("generate-btn-container").classList.add("hidden");
            document.getElementById("deployment-section").classList.add("hidden");

            chatInput.disabled = false;
            sendBtn.disabled = false;

            chatMessages.innerHTML = "";
            if (data.specialist_greeting) {
                appendBubble(data.specialist_greeting, "bot-bubble");
                conversationHistory.push({
                    role: "agent",
                    response_text: data.specialist_greeting,
                    timestamp: new Date().toISOString()
                });
            }
        } catch (err) {
            console.error("[AppSheet Creator Studio] Error loading agent session:", err);
            alert(`Error loading agent session from Management App: ${err.message}`);
        } finally {
            hideLoading();
        }
    });

    // 3. Save Agent to Management App
    saveMgmtBtn.addEventListener("click", async () => {
        const appId = appIdInput.value.trim();
        const accessKey = accessKeyInput.value.trim();
        const email = getCurrentUserEmail();

        console.log("[AppSheet Creator Studio] Saving agent to Management App:", { appId, email });

        if (!email) {
            alert("Please sign in with Google or enter your user email first.");
            return;
        }

        if (!appId || !accessKey) {
            alert("Please enter App ID and Access Key before saving.");
            return;
        }

        const tablesCount = Object.keys(activeTables).length;
        if (tablesCount === 0) {
            const proceed = confirm("⚠️ No table schemas have been parsed or uploaded for this agent yet. Saving now will only persist your connection credentials (without schemas). Do you want to proceed?");
            if (!proceed) return;
        }

        showLoading("Saving Agent to Management App...", `Persisting record for '${appId}' under ${email}...`);

        const formData = new FormData();
        formData.append("app_id", appId);
        formData.append("appsheet_key", accessKey);
        formData.append("user_email", email);
        formData.append("status", "Draft");

        try {
            const resp = await fetch("/api/management/save_agent", {
                method: "POST",
                body: formData
            });

            const data = await resp.json();
            console.log("[AppSheet Creator Studio] Save agent response:", data);
            if (!resp.ok) throw new Error(data.detail);

            alert(`✅ Agent '${appId}' saved to AppSheet Management App for user ${email}!`);
            window.fetchSavedAgents(appId);
        } catch (err) {
            console.error("[AppSheet Creator Studio] Save agent error:", err);
            alert(`Error saving to Management App: ${err.message}`);
        } finally {
            hideLoading();
        }
    });

    // 4. Upload and Parse openapi.json & Start Specialist Greeting
    uploadForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        if (!openapiInput.files[0]) {
            alert("Please select openapi.json file.");
            return;
        }

        console.log("[AppSheet Creator Studio] Uploading & parsing openapi.json file...");
        showLoading("Parsing OpenAPI & Documentation...", "Extracting table schemas & preparing Specialist Agent Architect...");

        const formData = new FormData();
        formData.append("openapi_file", openapiInput.files[0]);
        if (docInput.files[0]) {
            formData.append("doc_file", docInput.files[0]);
        }

        parseStatus.className = "status-box";
        parseStatus.innerText = "Parsing openapi.json & starting Specialist Agent consulting...";

        try {
            const resp = await fetch("/api/upload_and_parse", {
                method: "POST",
                body: formData
            });

            const data = await resp.json();
            console.log("[AppSheet Creator Studio] Parse response:", data);
            if (!resp.ok) throw new Error(data.detail || "Parse failed");

            parsedAppData = data;
            activeTables = data.table_details || {};
            activeCapabilities = [];
            localStorage.setItem("appsheet_active_tables", JSON.stringify(activeTables));

            parseStatus.style.background = "rgba(56, 189, 248, 0.15)";
            parseStatus.innerText = `✅ Parsed '${data.app_title}'! Found ${data.tables_found.length} tables. Specialist Agent ready!`;

            if (data.app_id) appIdInput.value = data.app_id;

            // Reset progressive disclosure states
            generateBtn.disabled = true;
            document.getElementById("generate-btn-container").classList.add("hidden");
            document.getElementById("deployment-section").classList.add("hidden");

            chatInput.disabled = false;
            sendBtn.disabled = false;

            chatMessages.innerHTML = "";
            if (data.specialist_greeting) {
                appendBubble(data.specialist_greeting, "bot-bubble");
                conversationHistory.push({
                    role: "agent",
                    response_text: data.specialist_greeting,
                    timestamp: new Date().toISOString()
                });
            }
        } catch (err) {
            console.error("[AppSheet Creator Studio] Parse error:", err);
            parseStatus.style.background = "rgba(239, 68, 68, 0.15)";
            parseStatus.innerText = `❌ Error: ${err.message}`;
        } finally {
            hideLoading();
        }
    });

    // 5. Generate Agent Code & ARD Spec with Configured Service URL & Antigravity Advanced Features
    generateBtn.addEventListener("click", async () => {
        const appId = appIdInput.value.trim();
        const accessKey = accessKeyInput.value.trim();
        const region = regionSelect.value;
        const serviceUrl = serviceUrlInput.value.trim() || "https://appsheet-agent-xyz.a.run.app";
        const email = getCurrentUserEmail();
        const vertexMode = vertexModeCheckbox.checked ? "true" : "false";
        const gcpProject = gcpProjectInput.value.trim();

        console.log("[AppSheet Creator Studio] Generating Agent Package...", { appId, region, serviceUrl, email, vertexMode, gcpProject });

        if (!appId || !accessKey) {
            alert("Please provide App ID and Access Key.");
            return;
        }

        showLoading("Building Antigravity SDK Agent...", "Scaffolding Security Policies, Multimodal Ingestion & @tool functions...");

        const formData = new FormData();
        formData.append("app_id", appId);
        formData.append("access_key", accessKey);
        formData.append("region", region);
        formData.append("service_url", serviceUrl);
        formData.append("user_email", email);
        formData.append("vertex_mode", vertexMode);
        formData.append("gcp_project", gcpProject);

        if (activeTables && Object.keys(activeTables).length > 0) {
            formData.append("client_tables_json", JSON.stringify(activeTables));
        }
        if (activeCapabilities && activeCapabilities.length > 0) {
            formData.append("client_capabilities_json", JSON.stringify(activeCapabilities));
        }

        try {
            const resp = await fetch("/api/generate_agent", {
                method: "POST",
                body: formData
            });

            const data = await resp.json();
            console.log("[AppSheet Creator Studio] Generate Agent response:", data);
            if (!resp.ok) throw new Error(data.detail);

            latestRegistrationJson = data.gemini_registration_json;
            jsonOutput.innerText = JSON.stringify(latestRegistrationJson, null, 2);

            // Populate customized deployment script
            deployCommandsOutput.innerText = buildCustomizedDeploymentScript(appId, accessKey, region, serviceUrl);
            showDeployGuideBtn.disabled = false;

            // Reveal the Deployment & Registration Section
            const deploySection = document.getElementById("deployment-section");
            if (deploySection) deploySection.classList.remove("hidden");

            if (data.zip_base64) {
                latestZipBase64 = data.zip_base64;
                downloadZipBtn.disabled = false;
                
                // Trigger automatic browser download for the .zip file!
                triggerZipDownload(data.zip_base64, `appsheet_agent_package_${appId}.zip`);
                alert(`✅ Antigravity SDK Agent Package downloaded: 'appsheet_agent_package_${appId}.zip'!\n\nSecurity Policies, Multimodal Image Ingestion & Custom Deployment Commands are included below.`);
            } else {
                alert("✅ Antigravity SDK Agent Package & ARD Spec generated! Security Policies, Multimodal Ingestion & Custom Deployment Commands are included below.");
            }
        } catch (err) {
            console.error("[AppSheet Creator Studio] Generate Agent error:", err);
            alert(`Error: ${err.message}`);
        } finally {
            hideLoading();
        }
    });

    // Dynamically update JSON payload and deployment commands when Deployed Service URL changes
    serviceUrlInput.addEventListener("input", () => {
        const newUrl = serviceUrlInput.value.trim();
        const appId = appIdInput.value.trim();
        const accessKey = accessKeyInput.value.trim();
        const region = regionSelect.value;

        if (latestRegistrationJson) {
            latestRegistrationJson.url = newUrl;
            jsonOutput.innerText = JSON.stringify(latestRegistrationJson, null, 2);
        }

        if (appId) {
            deployCommandsOutput.innerText = buildCustomizedDeploymentScript(appId, accessKey, region, newUrl);
        }
    });

    // Dynamically update deployment commands when region changes
    regionSelect.addEventListener("change", () => {
        const newUrl = serviceUrlInput.value.trim();
        const appId = appIdInput.value.trim();
        const accessKey = accessKeyInput.value.trim();
        const region = regionSelect.value;

        if (appId) {
            deployCommandsOutput.innerText = buildCustomizedDeploymentScript(appId, accessKey, region, newUrl);
        }
    });

    // Toggle Cloud Run Deployment Guide Box
    showDeployGuideBtn.addEventListener("click", () => {
        if (deployGuideBox.classList.contains("hidden")) {
            deployGuideBox.classList.remove("hidden");
            showDeployGuideBtn.innerText = "Hide Deployment Commands";
        } else {
            deployGuideBox.classList.add("hidden");
            showDeployGuideBtn.innerText = "🚀 Cloud Run Deployment Commands";
        }
    });

    copyDeployScriptBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(deployCommandsOutput.innerText);
        copyDeployScriptBtn.innerText = "Copied Script!";
        setTimeout(() => copyDeployScriptBtn.innerText = "Copy Script", 2000);
    });

    // Manual Download Button Handler for .zip Package
    downloadZipBtn.addEventListener("click", () => {
        const appId = appIdInput.value.trim() || "agent";
        if (latestZipBase64) {
            triggerZipDownload(latestZipBase64, `appsheet_agent_package_${appId}.zip`);
        } else {
            alert("Please click 'Generate Agent & ARD Spec' first to create the zip package.");
        }
    });

    // 6. Specialist Agent Design Dialogue & 2-Phase Plan Generation
    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        const appId = appIdInput.value.trim();
        const accessKey = accessKeyInput.value.trim();
        const region = regionSelect.value;
        const email = getCurrentUserEmail();

        console.log("[AppSheet Creator Studio] Sending creator dialogue turn:", text);

        appendBubble(text, "user-bubble");
        chatInput.value = "";

        const userTurn = {
            role: "creator",
            message: text,
            user_email: email,
            app_id: appId,
            timestamp: new Date().toISOString()
        };
        conversationHistory.push(userTurn);

        showLoading("Specialist Agent Architect Thinking...", "Evaluating requirement & generating A2UI v0.8 card previews...");

        const formData = new FormData();
        formData.append("message", text);
        formData.append("app_id", appId);
        formData.append("access_key", accessKey);
        formData.append("region", region);
        formData.append("user_email", email);

        if (activeTables && Object.keys(activeTables).length > 0) {
            formData.append("client_tables_json", JSON.stringify(activeTables));
        }
        if (activeCapabilities && activeCapabilities.length > 0) {
            formData.append("client_capabilities_json", JSON.stringify(activeCapabilities));
        }

        try {
            const resp = await fetch("/api/specialist_chat", {
                method: "POST",
                body: formData
            });

            const data = await resp.json();
            console.log("[AppSheet Creator Studio] Specialist Agent response:", data);
            console.info(`%c🤖 Specialist Agent Routing Mode: ${data.routing_mode || "Unknown"}`, "color: #1a73e8; font-weight: bold; font-size: 1.1em;");
            if (data.error_message) {
                console.warn("[AppSheet Creator Studio] Specialist Agent error/fallback detail:", data.error_message);
            }
            if (data.capabilities) activeCapabilities = data.capabilities;

            const botBubble = document.createElement("div");
            botBubble.className = "chat-bubble bot-bubble";
            
            const textSpan = document.createElement("div");
            textSpan.innerHTML = formatMarkdown(data.response_text);
            botBubble.appendChild(textSpan);

            if (data.a2ui_commands && data.a2ui_commands.length > 0) {
                const cardDom = A2UIRenderer.renderCommands(data.a2ui_commands);
                botBubble.appendChild(cardDom);

                // Also update the simulated phone surface on the right column!
                const phoneSurface = document.getElementById("phone-preview-surface");
                if (phoneSurface) {
                    phoneSurface.innerHTML = "";
                    phoneSurface.appendChild(cardDom.cloneNode(true));
                }
            }

            if (data.generated_tool_code) {
                const details = document.createElement("details");
                details.style.marginTop = "10px";
                details.style.cursor = "pointer";
                
                const summary = document.createElement("summary");
                summary.style.fontWeight = "600";
                summary.style.color = "var(--accent)";
                summary.style.outline = "none";
                summary.innerText = "🛠️ View Generated Agent Tool Code";
                
                const codeBlock = document.createElement("pre");
                codeBlock.className = "tool-code-preview";
                codeBlock.style.marginTop = "6px";
                codeBlock.style.background = "rgba(15, 23, 42, 0.4)";
                codeBlock.style.border = "1px solid rgba(255, 255, 255, 0.08)";
                codeBlock.innerText = data.generated_tool_code;
                
                details.appendChild(summary);
                details.appendChild(codeBlock);
                botBubble.appendChild(details);
            }

            // Quick-action button to propose the plan instead of requiring typing
            if (!data.is_plan_proposal && data.capabilities && data.capabilities.length > 0) {
                const btnWrapper = document.createElement("div");
                btnWrapper.style.marginTop = "12px";

                const proceedBtn = document.createElement("button");
                proceedBtn.className = "btn btn-primary";
                proceedBtn.style.padding = "8px 16px";
                proceedBtn.style.fontSize = "0.85rem";
                proceedBtn.style.background = "linear-gradient(135deg, #06b6d4, #3b82f6)";
                proceedBtn.style.color = "#0f172a";
                proceedBtn.innerText = "📋 Propose Agent Plan";
                
                proceedBtn.addEventListener("click", () => {
                    chatInput.value = "proceed";
                    sendMessage();
                    btnWrapper.remove(); // Remove wrapper to clean up the bubble
                });
                
                btnWrapper.appendChild(proceedBtn);
                botBubble.appendChild(btnWrapper);
            }

            chatMessages.appendChild(botBubble);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            // Show and enable Generate button when the implementation plan has been proposed
            if (data.is_plan_proposal) {
                const genBtnContainer = document.getElementById("generate-btn-container");
                if (genBtnContainer) genBtnContainer.classList.remove("hidden");
                generateBtn.disabled = false;
            }

            const agentTurn = {
                role: "specialist_agent",
                routing_mode: data.routing_mode || "Unknown",
                error_message: data.error_message || null,
                response_text: data.response_text,
                capabilities: data.capabilities || [],
                a2ui_commands: data.a2ui_commands || [],
                generated_tool_code: data.generated_tool_code || "",
                timestamp: new Date().toISOString()
            };
            conversationHistory.push(agentTurn);
        } catch (err) {
            console.error("[AppSheet Creator Studio] Specialist chat error:", err);
            appendBubble(`❌ Specialist consultation error: ${err.message}`, "bot-bubble");
            conversationHistory.push({
                role: "error",
                error: err.message,
                timestamp: new Date().toISOString()
            });
        } finally {
            hideLoading();
        }
    }

    sendBtn.addEventListener("click", sendMessage);
    chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendMessage();
    });

    // 7. Download Specialist Design Log as JSON
    downloadChatBtn.addEventListener("click", () => {
        if (conversationHistory.length === 0) {
            alert("No Specialist Agent design log to download yet.");
            return;
        }

        console.log("[AppSheet Creator Studio] Exporting design log JSON...");
        const exportPayload = {
            export_timestamp: new Date().toISOString(),
            app_id: appIdInput.value.trim(),
            user_email: getCurrentUserEmail(),
            turns: conversationHistory
        };

        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportPayload, null, 2));
        const downloadAnchor = document.createElement('a');
        downloadAnchor.setAttribute("href", dataStr);
        downloadAnchor.setAttribute("download", `appsheet_agent_design_log_${Date.now()}.json`);
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();
    });

    copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(jsonOutput.innerText);
        copyBtn.innerText = "Copied!";
        setTimeout(() => copyBtn.innerText = "Copy JSON", 2000);
    });

    // 8. OAuth 2.0 Credentials Registration Helper
    const oauthClientIdInput = document.getElementById("oauth-client-id");
    const copyAuthUrlBtn = document.getElementById("copy-auth-url-btn");
    const authUrlOutput = document.getElementById("auth-url-output");
    const copyTokenUrlBtn = document.getElementById("copy-token-url-btn");
    const copyScopesBtn = document.getElementById("copy-scopes-btn");

    function updateAuthUrl() {
        const clientId = oauthClientIdInput.value.trim();
        if (!clientId) {
            authUrlOutput.innerText = "Please enter your Client ID above...";
            copyAuthUrlBtn.disabled = true;
            return;
        }

        const base = "https://accounts.google.com/o/oauth2/v2/auth";
        const params = new URLSearchParams({
            client_id: clientId,
            redirect_uri: "https://vertexaisearch.cloud.google.com/static/oauth/oauth.html",
            scope: "https://www.googleapis.com/auth/userinfo.email",
            include_granted_scopes: "true",
            response_type: "code",
            access_type: "offline",
            prompt: "consent"
        });

        const authUrl = `${base}?${params.toString()}`;
        authUrlOutput.innerText = authUrl;
        copyAuthUrlBtn.disabled = false;
    }

    oauthClientIdInput.addEventListener("input", updateAuthUrl);

    copyAuthUrlBtn.addEventListener("click", () => {
        const text = authUrlOutput.innerText;
        if (text && !text.startsWith("Please enter")) {
            navigator.clipboard.writeText(text);
            copyAuthUrlBtn.innerText = "Copied!";
            setTimeout(() => copyAuthUrlBtn.innerText = "Copy", 2000);
        }
    });

    copyTokenUrlBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(document.getElementById("token-url-output").innerText);
        copyTokenUrlBtn.innerText = "Copied!";
        setTimeout(() => copyTokenUrlBtn.innerText = "Copy", 2000);
    });

    copyScopesBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(document.getElementById("scopes-output").innerText);
        copyScopesBtn.innerText = "Copied!";
        setTimeout(() => copyScopesBtn.innerText = "Copy", 2000);
    });

    function appendBubble(text, className) {
        const div = document.createElement("div");
        div.className = `chat-bubble ${className}`;
        div.innerHTML = formatMarkdown(text);
        chatMessages.appendChild(div);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});

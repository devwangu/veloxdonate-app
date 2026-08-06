const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');

if (!token) {
    document.body.innerHTML = "<h2 style='text-align:center; margin-top:20vh; color:#ef4444;'>❌ ไม่อนุญาตให้เข้าถึง (Unauthorized) <br><br>กรุณาเปิดผ่านไฟล์ run_controller.bat</h2>";
}

const headers = {
    'Content-Type': 'application/json'
};

let regexFormats = [];
let currentModalIndex = -1;
let lastFetchedOCRText = "";

// Load Config
async function loadConfig() {
    try {
        const res = await fetch(`/api/admin/config?token=${token}`);
        if (!res.ok) {
            if (res.status === 401) {
                throw new Error("Token สิทธิ์การเข้าถึงไม่ถูกต้อง หรือเซิร์ฟเวอร์รีสตาร์ท กรุณาเข้าผ่านลิงก์ Controller ใหม่");
            }
            const text = await res.text();
            throw new Error(`เซิร์ฟเวอร์ตอบกลับผิดพลาด (${res.status}): ${text.substring(0, 80)}`);
        }
        const data = await res.json();
        if (data.error) throw new Error(data.error);

        if (document.getElementById('streamer-name')) document.getElementById('streamer-name').value = data.streamer_name || '';
        document.getElementById('promptpay-id').value = data.promptpay_id || '';
        document.getElementById('minimum-donation').value = data.minimum_donation || 10.0;
        document.getElementById('window-select').value = data.line_window_title || '';
        if (document.getElementById('cfg-line-window-title')) document.getElementById('cfg-line-window-title').value = data.line_window_title || '';
        if (document.getElementById('velox-donate-token')) document.getElementById('velox-donate-token').value = data.velox_donate_token || '';
        if (document.getElementById('portal-url')) document.getElementById('portal-url').value = data.portal_url || 'https://donate.veloxgg.com';
        
        renderNetworkModeUI(data);
        
        // Set static OBS Widget URLs
        const alertInput = document.getElementById('url-widget-alert');
        if (alertInput) alertInput.value = `${window.location.origin}/widget/alert?token=${token}`;
        const topInput = document.getElementById('url-widget-top');
        if (topInput) topInput.value = `${window.location.origin}/widget/top?token=${token}`;
        const recentInput = document.getElementById('url-widget-recent');
        if (recentInput) recentInput.value = `${window.location.origin}/widget/recent?token=${token}`;
        const goalInput = document.getElementById('url-widget-goal');
        if (goalInput) goalInput.value = `${window.location.origin}/widget/goal?token=${token}`;
        
        regexFormats = data.regex_formats || [];
        renderRegexList();
        
        // Populate Alert Config
        if (data.alert_config) {
            const ac = data.alert_config;
            if (ac.color_name) document.getElementById('cfg-color-name').value = ac.color_name;
            if (ac.color_amount) document.getElementById('cfg-color-amount').value = ac.color_amount;
            if (ac.color_message) document.getElementById('cfg-color-message').value = ac.color_message;
            if (ac.template_text) document.getElementById('cfg-template-text').value = ac.template_text;
            if (ac.image_url) document.getElementById('cfg-image-url').value = ac.image_url;
            if (ac.image_position) document.getElementById('cfg-image-position').value = ac.image_position;
            if (ac.font_family) document.getElementById('cfg-font-family').value = ac.font_family;
            if (ac.font_size) {
                document.getElementById('cfg-font-size').value = ac.font_size;
                document.getElementById('val-font-size').textContent = ac.font_size;
            }
            if (ac.duration) {
                document.getElementById('cfg-duration').value = ac.duration;
                document.getElementById('val-duration').textContent = ac.duration;
            }
            if (ac.anim_in) document.getElementById('cfg-anim-in').value = ac.anim_in;
            if (ac.anim_out) document.getElementById('cfg-anim-out').value = ac.anim_out;
            if (ac.sound_effect) document.getElementById('cfg-sound-effect').value = ac.sound_effect;
            if (ac.sound_volume !== undefined) {
                document.getElementById('cfg-sound-volume').value = ac.sound_volume;
                document.getElementById('val-volume').textContent = ac.sound_volume;
            }
            if (ac.enable_tts !== undefined && document.getElementById('cfg-enable-tts')) document.getElementById('cfg-enable-tts').checked = ac.enable_tts;
            if (ac.tts_voice && document.getElementById('cfg-tts-voice')) document.getElementById('cfg-tts-voice').value = ac.tts_voice;
            if (ac.min_display !== undefined && document.getElementById('cfg-min-display')) document.getElementById('cfg-min-display').value = ac.min_display;
        }

        // Populate Top Donator Config
        if (data.top_donator_config) {
            const tc = data.top_donator_config;
            if (tc.start_date !== undefined) document.getElementById('top-cfg-start-date').value = tc.start_date;
            if (tc.color_name) document.getElementById('top-cfg-color-name').value = tc.color_name;
            if (tc.color_amount) document.getElementById('top-cfg-color-amount').value = tc.color_amount;
            if (tc.font_family_name) document.getElementById('top-cfg-font-name').value = tc.font_family_name;
            if (tc.font_family_amount) document.getElementById('top-cfg-font-amount').value = tc.font_family_amount;
            if (tc.font_size_name) {
                document.getElementById('top-cfg-font-size-name').value = tc.font_size_name;
                document.getElementById('val-top-font-size-name').textContent = tc.font_size_name;
            }
            if (tc.font_size_amount) {
                document.getElementById('top-cfg-font-size-amount').value = tc.font_size_amount;
                document.getElementById('val-top-font-size-amount').textContent = tc.font_size_amount;
            }
            if (tc.item_gap !== undefined) {
                document.getElementById('top-cfg-item-gap').value = tc.item_gap;
                document.getElementById('val-top-item-gap').textContent = tc.item_gap;
            }
            if (tc.layout_mode) {
                const r = document.querySelector(`input[name="top-layout-mode"][value="${tc.layout_mode}"]`);
                if (r) r.checked = true;
            }
            if (tc.limit) document.getElementById('top-cfg-limit').value = tc.limit;
            if (tc.filter_badwords !== undefined) document.getElementById('top-cfg-filter-badwords').checked = tc.filter_badwords;
            if (tc.custom_badwords !== undefined) document.getElementById('top-cfg-custom-badwords').value = tc.custom_badwords;

            updateTopPreview();
        }

        // Populate Recent Donator Config
        if (data.recent_donator_config) {
            const rc = data.recent_donator_config;
            if (rc.color_name) document.getElementById('recent-cfg-color-name').value = rc.color_name;
            if (rc.color_amount) document.getElementById('recent-cfg-color-amount').value = rc.color_amount;
            if (rc.font_family_name) document.getElementById('recent-cfg-font-name').value = rc.font_family_name;
            if (rc.font_family_amount) document.getElementById('recent-cfg-font-amount').value = rc.font_family_amount;
            if (rc.font_size_name) {
                document.getElementById('recent-cfg-font-size-name').value = rc.font_size_name;
                document.getElementById('val-recent-font-size-name').textContent = rc.font_size_name;
            }
            if (rc.font_size_amount) {
                document.getElementById('recent-cfg-font-size-amount').value = rc.font_size_amount;
                document.getElementById('val-recent-font-size-amount').textContent = rc.font_size_amount;
            }
            if (rc.item_gap !== undefined) {
                document.getElementById('recent-cfg-item-gap').value = rc.item_gap;
                document.getElementById('val-recent-item-gap').textContent = rc.item_gap;
            }
            if (rc.layout_mode) {
                const r = document.querySelector(`input[name="recent-layout-mode"][value="${rc.layout_mode}"]`);
                if (r) r.checked = true;
            }
            if (rc.limit) document.getElementById('recent-cfg-limit').value = rc.limit;
            if (rc.filter_badwords !== undefined) document.getElementById('recent-cfg-filter-badwords').checked = rc.filter_badwords;
            if (rc.custom_badwords !== undefined) document.getElementById('recent-cfg-custom-badwords').value = rc.custom_badwords;

            updateRecentPreview();
        }

        // Populate Goal Config
        if (data.goal_config) {
            const gc = data.goal_config;
            if (gc.title !== undefined) document.getElementById('goal-cfg-title').value = gc.title;
            if (gc.start_date !== undefined) document.getElementById('goal-cfg-start-date').value = gc.start_date;
            if (gc.end_date !== undefined) document.getElementById('goal-cfg-end-date').value = gc.end_date;
            if (gc.target_amount !== undefined) document.getElementById('goal-cfg-target').value = gc.target_amount;
            if (gc.initial_amount !== undefined) document.getElementById('goal-cfg-initial').value = gc.initial_amount;
            if (gc.color_bar) document.getElementById('goal-cfg-color-bar').value = gc.color_bar;
            if (gc.color_bg) document.getElementById('goal-cfg-color-bg').value = gc.color_bg;
            if (gc.color_text) document.getElementById('goal-cfg-color-text').value = gc.color_text;
            if (gc.font_family_title) document.getElementById('goal-cfg-font-title').value = gc.font_family_title;
            if (gc.font_family_number) document.getElementById('goal-cfg-font-number').value = gc.font_family_number;
            if (gc.font_size) {
                document.getElementById('goal-cfg-font-size').value = gc.font_size;
                document.getElementById('val-goal-font-size').textContent = gc.font_size;
            }

            updateGoalPreview();
        }

        await loadMediaLists(data.alert_config ? data.alert_config.image_url : null, data.alert_config ? data.alert_config.sound_effect : null);
        await loadWindows(data.line_window_title);
    } catch (e) {
        console.error(e);
        alert("โหลดการตั้งค่าล้มเหลว: " + e.message);
    }
}

// Fetch available windows
async function loadWindows(selectedTitle = null) {
    const select = document.getElementById('window-select');
    select.innerHTML = '<option value="">กำลังโหลด...</option>';
    
    try {
        const res = await fetch(`/api/admin/windows?token=${token}`);
        const data = await res.json();
        
        select.innerHTML = '<option value="">-- ปล่อยว่างเพื่อค้นหาคำว่า ChatWindow อัตโนมัติ --</option>';
        data.windows.forEach(w => {
            const option = document.createElement('option');
            option.value = w;
            option.textContent = w;
            if (w === selectedTitle) option.selected = true;
            select.appendChild(option);
        });
    } catch (e) {
        console.error(e);
        select.innerHTML = '<option value="">โหลดรายชื่อหน้าต่างล้มเหลว</option>';
    }
}

// Save Config
async function saveConfig() {
    // Update regexFormats from inputs
    const regexCards = document.querySelectorAll('.regex-card');
    regexFormats = Array.from(regexCards).map(card => {
        const index = card.dataset.index;
        return {
            name: document.getElementById(`regex-name-${index}`).value,
            pattern: document.getElementById(`regex-pattern-${index}`).value,
            type: document.getElementById(`regex-type-${index}`).value
        };
    });

    const payload = {
        streamer_name: document.getElementById('streamer-name') ? document.getElementById('streamer-name').value : '',
        promptpay_id: document.getElementById('promptpay-id').value,
        minimum_donation: parseFloat(document.getElementById('minimum-donation').value),
        line_window_title: (document.getElementById('cfg-line-window-title') && document.getElementById('cfg-line-window-title').value.trim()) 
            ? document.getElementById('cfg-line-window-title').value.trim() 
            : (document.getElementById('window-select') ? document.getElementById('window-select').value : ''),
        velox_donate_token: document.getElementById('velox-donate-token') ? document.getElementById('velox-donate-token').value : '',
        portal_url: document.getElementById('portal-url') ? document.getElementById('portal-url').value : '',
        network_mode: currentNetworkMode,
        regex_formats: regexFormats,
        token: token
    };

    try {
        const res = await fetch(`/api/admin/config`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(payload)
        });
        if (!res.ok) {
            const text = await res.text();
            throw new Error(`HTTP ${res.status}: ${text.substring(0, 80)}`);
        }
        const data = await res.json();
        if (data.success) {
            showToast("💾 บันทึกข้อมูลระบบสำเร็จ!");
            loadConfig();
        } else {
            showToast("❌ บันทึกไม่สำเร็จ: " + data.error);
        }
    } catch (e) {
        showToast("❌ เกิดข้อผิดพลาดในการบันทึก: " + e.message);
    }
}

let currentNetworkMode = 2;

function renderNetworkModeUI(data) {
    currentNetworkMode = data.network_mode || (data.velox_donate_token ? 2 : 1);

    const cardMode1 = document.getElementById('card-mode-1');
    const cardMode2 = document.getElementById('card-mode-2');
    const badgeMode1 = document.getElementById('badge-mode-1');
    const badgeMode2 = document.getElementById('badge-mode-2');
    const statusText = document.getElementById('mode2-status-text');
    const actionBtns = document.getElementById('mode2-action-btns');
    const btnMode2 = document.getElementById('btn-mode-2-activate');

    if (currentNetworkMode === 1) {
        if (cardMode1) {
            cardMode1.style.border = '2px solid rgba(16, 185, 129, 0.4)';
            cardMode1.style.background = 'rgba(16, 185, 129, 0.08)';
        }
        if (badgeMode1) {
            badgeMode1.innerHTML = '🟢 กำลังใช้งานอยู่ (Active)';
            badgeMode1.style.background = '#059669';
            badgeMode1.style.color = '#ffffff';
        }
        if (cardMode2) {
            cardMode2.style.border = '1px solid rgba(255, 255, 255, 0.1)';
            cardMode2.style.background = 'rgba(255, 255, 255, 0.03)';
        }
        if (badgeMode2) {
            badgeMode2.innerHTML = '⚪ ปิดใช้งานอยู่';
            badgeMode2.style.background = 'rgba(255,255,255,0.1)';
            badgeMode2.style.color = '#94a3b8';
        }
        if (btnMode2) {
            btnMode2.innerHTML = '<i class="fa-solid fa-bolt"></i> เปิดใช้งาน VeloxGG Mode';
            btnMode2.style.background = 'linear-gradient(135deg, #9333ea, #6366f1)';
            btnMode2.style.color = '#ffffff';
            btnMode2.style.border = 'none';
            btnMode2.onclick = () => switchNetworkMode(2);
        }
    } else {
        if (cardMode2) {
            cardMode2.style.border = '2px solid rgba(168, 85, 247, 0.4)';
            cardMode2.style.background = 'rgba(168, 85, 247, 0.05)';
        }
        if (badgeMode2) {
            badgeMode2.innerHTML = '🟢 กำลังใช้งานอยู่ (Active)';
            badgeMode2.style.background = '#059669';
            badgeMode2.style.color = '#ffffff';
        }
        if (cardMode1) {
            cardMode1.style.border = '1px solid rgba(255, 255, 255, 0.1)';
            cardMode1.style.background = 'rgba(255, 255, 255, 0.03)';
        }
        if (badgeMode1) {
            badgeMode1.innerHTML = '⚪ ปิดใช้งานอยู่';
            badgeMode1.style.background = 'rgba(255,255,255,0.1)';
            badgeMode1.style.color = '#94a3b8';
        }
        if (btnMode2) {
            btnMode2.innerHTML = '<i class="fa-solid fa-power-off"></i> ปิดใช้งาน VeloxGG Mode (สลับไปใช้ Cloudflare Mode)';
            btnMode2.style.background = 'rgba(239, 68, 68, 0.2)';
            btnMode2.style.color = '#fca5a5';
            btnMode2.style.border = '1px solid rgba(239, 68, 68, 0.4)';
            btnMode2.onclick = () => switchNetworkMode(1);
        }
    }

    // VeloxGG Status Badge Top Header & Token Input Locking
    const veloxStatusBadge = document.getElementById('velox-status-badge');
    const tokenInput = document.getElementById('velox-donate-token');
    const tokenVal = (tokenInput ? tokenInput.value : '').trim();
    const portalUrl = (document.getElementById('portal-url') ? document.getElementById('portal-url').value : 'https://donate.veloxgg.com').replace(/\/+$/, '');

    if (currentNetworkMode === 2 && data.synced_slug) {
        window.__VELOX_URL__ = `${portalUrl}/${data.synced_slug}`;
        if (veloxStatusBadge) {
            const displayHost = portalUrl.replace(/^https?:\/\//, '');
            veloxStatusBadge.innerHTML = `🟢 ซิงค์สำเร็จ (${displayHost}/${data.synced_slug})`;
            veloxStatusBadge.style.background = 'rgba(16, 185, 129, 0.2)';
            veloxStatusBadge.style.color = '#34d399';
            veloxStatusBadge.style.border = '1px solid rgba(16, 185, 129, 0.4)';
        }
    } else if (currentNetworkMode === 2 && data.sync_error) {
        window.__VELOX_URL__ = '';
        if (veloxStatusBadge) {
            veloxStatusBadge.innerHTML = '🔴 Token ไม่ถูกต้อง';
            veloxStatusBadge.style.background = 'rgba(239, 68, 68, 0.2)';
            veloxStatusBadge.style.color = '#fca5a5';
            veloxStatusBadge.style.border = '1px solid rgba(239, 68, 68, 0.4)';
        }
    } else if (currentNetworkMode === 2) {
        window.__VELOX_URL__ = '';
        if (veloxStatusBadge) {
            veloxStatusBadge.innerHTML = '🟡 กำลังเชื่อมต่อระบบ VeloxGG Mode...';
            veloxStatusBadge.style.background = 'rgba(234, 179, 8, 0.2)';
            veloxStatusBadge.style.color = '#fde047';
            veloxStatusBadge.style.border = '1px solid rgba(234, 179, 8, 0.4)';
        }
    } else {
        window.__VELOX_URL__ = '';
        if (veloxStatusBadge) {
            veloxStatusBadge.innerHTML = '⚪ ไม่ได้เปิดใช้งาน VeloxGG Mode';
            veloxStatusBadge.style.background = 'rgba(255, 255, 255, 0.08)';
            veloxStatusBadge.style.color = '#94a3b8';
            veloxStatusBadge.style.border = '1px solid rgba(255, 255, 255, 0.15)';
        }
    }

    // Lock Token input when Mode 2 is Active & Connected
    if (currentNetworkMode === 2 && data.synced_slug) {
        if (tokenInput) {
            tokenInput.disabled = true;
            tokenInput.title = "ต้องปิดการเชื่อมต่อ VeloxGG Mode ก่อนจึงจะสามารถแก้ไข Token ได้";
            tokenInput.style.opacity = '0.6';
            tokenInput.style.cursor = 'not-allowed';
        }
    } else {
        if (tokenInput) {
            tokenInput.disabled = false;
            tokenInput.title = "";
            tokenInput.style.opacity = '1';
            tokenInput.style.cursor = 'text';
        }
    }

    if (!tokenVal) {
        if (statusText) statusText.innerHTML = '<span style="color: #f87171;"><i class="fa-solid fa-triangle-exclamation"></i> ยังไม่ได้ใส่ Velox Donate Token (คัดลอก Token จากหน้าเว็บมาวางแปะด้านบนได้เลย)</span>';
        if (actionBtns) actionBtns.innerHTML = '';
    } else if (data.sync_error && currentNetworkMode === 2) {
        if (statusText) statusText.innerHTML = `<span style="color: #f87171; font-weight:700;"><i class="fa-solid fa-circle-xmark"></i> ❌ ${escapeHtml(data.sync_error)}</span>`;
        if (actionBtns) actionBtns.innerHTML = '';
    } else if (data.synced_slug && currentNetworkMode === 2) {
        const fullCustomUrl = `${portalUrl}/${data.synced_slug}`;
        if (statusText) {
            statusText.innerHTML = `
                <div style="display:flex; flex-direction:column; gap:4px;">
                    <span style="color: #34d399; font-weight:700;"><i class="fa-solid fa-circle-check"></i> เชื่อมต่อสำเร็จ! พร้อมใช้งาน Custom URL</span>
                    <span style="color: #cbd5e1; font-size: 0.85rem; font-family: monospace;">🔗 ลิงก์ช่องของคุณ: <strong style="color:#a7f3d0;">${fullCustomUrl}</strong></span>
                </div>
            `;
        }
        if (actionBtns) {
            actionBtns.innerHTML = `
                <button class="btn" style="padding:6px 14px; font-size:0.8rem; background:rgba(59, 130, 246, 0.2); color:#60a5fa; border:1px solid rgba(59,130,246,0.4);" onclick="copyToClipboard('${fullCustomUrl}', 'คัดลอกลิงก์ประจำช่องเรียบร้อย!')">
                    <i class="fa-solid fa-copy"></i> คัดลอกลิงก์
                </button>
                <a href="${fullCustomUrl}" target="_blank" class="btn" style="padding:6px 14px; font-size:0.8rem; background:rgba(168, 85, 247, 0.2); color:#c084fc; border:1px solid rgba(168,85,247,0.4); text-decoration:none;">
                    <i class="fa-solid fa-arrow-up-right-from-square"></i> ลองเปิดดู
                </a>
            `;
        }
    } else {
        if (statusText) statusText.innerHTML = '<span style="color: #94a3b8;"><i class="fa-solid fa-hourglass-start"></i> กำลังรอคำสั่งสำหรับเชื่อมต่อ...</span>';
        if (actionBtns) actionBtns.innerHTML = '';
    }
}

function copyVeloxUrlTop() {
    if (!window.__VELOX_URL__) {
        showToast("⚠️ ยังไม่ได้เปิดใช้งาน VeloxGG Mode หรือยังไม่ได้ซิงค์ลิงก์ประจำช่อง");
        return;
    }
    copyToClipboard(window.__VELOX_URL__, "คัดลอกลิงก์ประจำช่อง VeloxGG เรียบร้อยแล้ว!");
}

function openVeloxUrlTop() {
    if (!window.__VELOX_URL__) {
        showToast("⚠️ ยังไม่ได้เปิดใช้งาน VeloxGG Mode หรือยังไม่ได้ซิงค์ลิงก์ประจำช่อง");
        return;
    }
    window.open(window.__VELOX_URL__, '_blank');
}

function clearTokenInput() {
    const input = document.getElementById('velox-donate-token');
    if (input) {
        if (input.disabled) {
            showToast("⚠️ ต้องกดปิดใช้งาน VeloxGG Mode ก่อนจึงจะสามารถเปลี่ยน/แก้ไข Token ได้ครับ");
            return;
        }
        input.value = '';
        input.focus();
        showToast("🧹 ล้างค่าช่อง Token เรียบร้อยแล้ว กรุณาวาง Token ใหม่ที่ได้จาก Dashboard ครับ");
    }
}

async function saveVeloxTokenOnly() {
    const tokenVal = document.getElementById('velox-donate-token') ? document.getElementById('velox-donate-token').value.trim() : '';
    if (!tokenVal) {
        showToast("⚠️ กรุณากรอก Velox Donate Token ก่อนบันทึกครับ");
        return;
    }
    const payload = {
        velox_donate_token: tokenVal,
        portal_url: document.getElementById('portal-url') ? document.getElementById('portal-url').value : '',
        token: token
    };
    try {
        const res = await fetch(`/api/admin/config`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast("💾 บันทึก Velox Donate Token สำเร็จแล้ว!");
            loadConfig();
        } else {
            showToast("❌ บันทึกไม่สำเร็จ: " + data.error);
        }
    } catch (e) {
        showToast("❌ เกิดข้อผิดพลาด: " + e.message);
    }
}

async function switchNetworkMode(mode) {
    currentNetworkMode = mode;
    const tokenVal = document.getElementById('velox-donate-token') ? document.getElementById('velox-donate-token').value.trim() : '';

    if (mode === 2 && !tokenVal) {
        showToast("⚠️ กรุณาใส่ Velox Donate Token ก่อนเปิดใช้งานโหมด 2 ครับ");
        if (document.getElementById('velox-donate-token')) document.getElementById('velox-donate-token').focus();
        return;
    }

    const btnMode2 = document.getElementById('btn-mode-2-activate');
    const statusText = document.getElementById('mode2-status-text');

    if (btnMode2) {
        btnMode2.disabled = true;
        if (mode === 2) {
            btnMode2.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> กำลังตรวจสอบ & สถาปนาอุโมงค์...';
        } else {
            btnMode2.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> กำลังยกเลิกอุโมงค์...';
        }
    }

    if (statusText) {
        if (mode === 2) {
            statusText.innerHTML = '<span style="color: #c084fc;"><i class="fa-solid fa-gear fa-spin"></i> ⚡ กำลังตรวจสอบความถูกต้องของ Token และสถาปนาอุโมงค์ Velox Gateway...</span>';
        } else {
            statusText.innerHTML = '<span style="color: #fca5a5;"><i class="fa-solid fa-gear fa-spin"></i> 🔴 กำลังปลดการผูกอุโมงค์ Velox Gateway และสลับกลับมาใช้ Cloudflare Mode...</span>';
        }
    }

    // 1.2 Seconds High-Tech Delay for smooth feedback
    await new Promise(r => setTimeout(r, 1200));

    const payload = {
        network_mode: mode,
        velox_donate_token: tokenVal,
        portal_url: document.getElementById('portal-url') ? document.getElementById('portal-url').value : '',
        token: token
    };

    try {
        const res = await fetch(`/api/admin/config`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok && data.success) {
            if (mode === 2) {
                showToast("⚡ สถาปนาการเชื่อมต่อและเปิดใช้งาน VeloxGG Mode สำเร็จ!");
            } else {
                showToast("🔴 ปิดใช้งาน VeloxGG Mode เรียบร้อยแล้ว (สลับกลับมาใช้ Cloudflare Mode)");
            }
            loadConfig();
        } else {
            showToast("❌ " + (data.error || "Token ไม่ถูกต้อง ไม่สามารถเปิดใช้งานโหมด 2 ได้"));
            loadConfig();
        }
    } catch (e) {
        showToast("❌ เกิดข้อผิดพลาด: " + e.message);
        loadConfig();
    } finally {
        if (btnMode2) {
            btnMode2.disabled = false;
        }
    }
}

function copyToClipboard(text, msg) {
    navigator.clipboard.writeText(text).then(() => {
        showToast("📋 " + (msg || "คัดลอกสำเร็จ!"));
    }).catch(err => {
        showToast("❌ ไม่สามารถคัดลอกได้: " + err);
    });
}

function renderRegexList() {
    const list = document.getElementById('regex-list');
    list.innerHTML = '';
    
    regexFormats.forEach((fmt, index) => {
        const card = document.createElement('div');
        card.className = 'regex-card';
        card.dataset.index = index;
        card.style = 'background: rgba(0,0,0,0.2); border: 1px solid var(--glass-border); border-radius: 8px; padding: 15px; margin-bottom: 10px; position: relative;';
        
        card.innerHTML = `
            <button class="btn" style="position: absolute; top: 10px; right: 10px; background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 5px 10px; width: auto;" onclick="removeRegex(${index})">
                <i class="fa-solid fa-trash"></i>
            </button>
            <div class="row" style="margin-bottom: 10px; padding-right: 40px;">
                <div class="col" style="flex: 2;">
                    <label style="font-size: 0.8rem;">ชื่อธนาคาร / คำอธิบาย</label>
                    <input type="text" class="form-control" id="regex-name-${index}" value="${fmt.name || ''}" placeholder="เช่น KBank เงินเข้า">
                </div>
                <div class="col" style="flex: 1;">
                    <label style="font-size: 0.8rem;">ประเภท</label>
                    <select class="form-control" id="regex-type-${index}">
                        <option value="in" ${fmt.type === 'in' ? 'selected' : ''}>เงินเข้า (In)</option>
                        <option value="out" ${fmt.type === 'out' ? 'selected' : ''}>เงินออก (Out)</option>
                    </select>
                </div>
            </div>
            <div class="row">
                <div class="col">
                    <label style="font-size: 0.8rem;">Regex Pattern</label>
                    <input type="text" class="form-control" id="regex-pattern-${index}" value="${fmt.pattern || ''}" placeholder="เช่น เงินเข้า\\+?([\\d,]+\\.\\d{2})" style="font-family: monospace;">
                </div>
            </div>
            <div class="row" style="margin-top: 10px;">
                <div class="col">
                    <button class="btn" style="background: rgba(139, 92, 246, 0.2); color: #c4b5fd; font-size: 0.8rem; padding: 5px 10px; width: auto;" onclick="autoGenerateRegex(${index})">
                        <i class="fa-solid fa-wand-magic-sparkles"></i> สร้างสูตรอัตโนมัติ (Auto-Generate)
                    </button>
                </div>
            </div>
        `;
        list.appendChild(card);
    });
    runLiveTest(); // update live tester when rendering
}

function addRegexFormat() {
    // Save current inputs to state before re-rendering
    const regexCards = document.querySelectorAll('.regex-card');
    regexFormats = Array.from(regexCards).map(card => {
        const index = card.dataset.index;
        return {
            name: document.getElementById(`regex-name-${index}`).value,
            pattern: document.getElementById(`regex-pattern-${index}`).value,
            type: document.getElementById(`regex-type-${index}`).value
        };
    });
    
    regexFormats.push({name: '', pattern: '', type: 'in'});
    renderRegexList();
}

function removeRegex(index) {
    if(confirm('ต้องการลบรูปแบบนี้ใช่หรือไม่?')) {
        regexFormats.splice(index, 1);
        renderRegexList();
    }
}

function autoGenerateRegex(index) {
    currentModalIndex = index;
    document.getElementById('modal-full-text').value = '';
    document.getElementById('modal-target-amount').value = '';
    
    const modal = document.getElementById('auto-gen-modal');
    modal.classList.add('show');
}

function closeAutoGenerateModal() {
    const modal = document.getElementById('auto-gen-modal');
    modal.classList.remove('show');
}

function confirmAutoGenerate() {
    if (currentModalIndex === -1) return;
    
    const fullText = document.getElementById('modal-full-text').value;
    const targetAmount = document.getElementById('modal-target-amount').value;
    
    if (!fullText || !targetAmount) {
        alert("กรุณากรอกข้อมูลให้ครบถ้วนครับ");
        return;
    }
    
    const flatText = fullText.replace(/[\n\s]/g, "");
    const flatTarget = targetAmount.replace(/,/g, "").trim();
    
    if (!flatTarget || !flatText) {
        alert("ข้อมูลไม่ถูกต้อง");
        return;
    }
    
    const idx = flatText.indexOf(flatTarget);
    if (idx === -1) {
        alert("❌ หาตัวเลขยอดเงิน (" + flatTarget + ") ไม่เจอในข้อความที่คุณใส่มาครับ กรุณาลองตรวจสอบอีกครั้ง");
        return;
    }
    
    let prefix = flatText.substring(Math.max(0, idx - 10), idx);
    prefix = prefix.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    prefix = prefix.replace(/\\\+$/, '\\+?').replace(/\\-$/, '\\-?');
    
    const finalPattern = prefix + "([\\d,]+\\.\\d{2})";
    
    document.getElementById(`regex-pattern-${currentModalIndex}`).value = finalPattern;
    closeAutoGenerateModal();
    runLiveTest(flatText);
    saveConfig();
}

function createNewPatternFromOCR() {
    if (!lastFetchedOCRText) {
        alert("ไม่พบข้อความจาก OCR กรุณากดทดสอบอ่านข้อความใหม่อีกครั้ง");
        return;
    }
    
    addRegexFormat();
    currentModalIndex = regexFormats.length - 1;
    
    document.getElementById('modal-full-text').value = lastFetchedOCRText;
    document.getElementById('modal-target-amount').value = '';
    
    const modal = document.getElementById('auto-gen-modal');
    modal.classList.add('show');
    
    setTimeout(() => {
        document.getElementById('modal-target-amount').focus();
    }, 300);
}

function toggleAccordion() {
    const content = document.getElementById('accordion-content');
    const icon = document.getElementById('accordion-icon');
    
    if (content.style.display === 'none' || !content.style.display) {
        content.style.display = 'block';
        icon.style.transform = 'rotate(180deg)';
    } else {
        content.style.display = 'none';
        icon.style.transform = 'rotate(0deg)';
    }
}

function switchTab(tabName) {
    document.querySelectorAll('.nav-tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    if (tabName === 'interceptor') {
        document.getElementById('btn-tab-interceptor')?.classList.add('active');
        document.getElementById('tab-interceptor')?.classList.add('active');
    } else if (tabName === 'widgets') {
        document.getElementById('btn-tab-widgets')?.classList.add('active');
        document.getElementById('tab-widgets')?.classList.add('active');
    } else if (tabName === 'setting') {
        document.getElementById('btn-tab-setting')?.classList.add('active');
        document.getElementById('tab-setting')?.classList.add('active');
    } else if (tabName === 'history') {
        document.getElementById('btn-tab-history')?.classList.add('active');
        document.getElementById('tab-history')?.classList.add('active');
        loadDonationHistory();
    } else if (tabName === 'network') {
        document.getElementById('btn-tab-network')?.classList.add('active');
        document.getElementById('tab-network')?.classList.add('active');
    }

    try {
        localStorage.setItem('active_controller_tab', tabName);
        if (history.replaceState) {
            history.replaceState(null, null, '#' + tabName);
        } else {
            window.location.hash = tabName;
        }
    } catch(e) {}
}

function restoreLastActiveTab() {
    let savedTab = window.location.hash ? window.location.hash.replace('#', '') : null;
    if (!savedTab) {
        savedTab = localStorage.getItem('active_controller_tab');
    }
    const validTabs = ['interceptor', 'widgets', 'setting', 'history', 'network'];
    if (savedTab && validTabs.includes(savedTab)) {
        switchTab(savedTab);
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

async function loadDonationHistory() {
    const tbody = document.getElementById('hist-table-body');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 30px; color: #94a3b8;"><i class="fa-solid fa-spinner fa-spin"></i> กำลังดึงข้อมูลจากฐานข้อมูล SQLite...</td></tr>';

    try {
        const res = await fetch(`/api/admin/donations?token=${token}`);
        if (!res.ok) throw new Error("ดึงข้อมูลล้มเหลว");
        const data = await res.json();

        const donations = data.donations || [];
        const stats = data.stats || { total_donations: 0, total_raised: 0 };

        document.getElementById('hist-total-raised').textContent = `฿${Number(stats.total_raised).toLocaleString('th-TH', {minimumFractionDigits: 0})}`;
        document.getElementById('hist-total-count').textContent = `${stats.total_donations} รายการ`;

        if (donations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 30px; color: #94a3b8;">ยังไม่มีประวัติการโดเนทในฐานข้อมูล</td></tr>';
            return;
        }

        tbody.innerHTML = donations.map(d => `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); transition: background 0.2s ease;" onmouseover="this.style.background='rgba(255,255,255,0.03)'" onmouseout="this.style.background='transparent'">
                <td style="padding: 12px 15px; color: #94a3b8; font-family: monospace;">#${d.id}</td>
                <td style="padding: 12px 15px; font-size: 0.85rem; color: #cbd5e1; white-space: nowrap;">${d.timestamp || '-'}</td>
                <td style="padding: 12px 15px; font-weight: 700; color: #f8fafc;">${escapeHtml(d.name || 'ผู้สนับสนุน')}</td>
                <td style="padding: 12px 15px; font-weight: 700; color: #34d399; font-family: monospace;">฿${Number(d.amount).toLocaleString('th-TH', {minimumFractionDigits: 0})}</td>
                <td style="padding: 12px 15px; color: #e2e8f0; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(d.message || '-')}</td>
                <td style="padding: 12px 15px;"><span style="background: rgba(52, 211, 153, 0.15); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.3); padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">${d.status || 'success'}</span></td>
                <td style="padding: 12px 15px; text-align: center;">
                    <button class="btn btn-danger" style="padding: 4px 10px; font-size: 0.75rem;" onclick="deleteSingleDonation('${d.id}')">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 30px; color: #ef4444;">เกิดข้อผิดพลาดในการโหลดข้อมูล: ${e.message}</td></tr>`;
    }
}

function filterDonationTable() {
    const query = document.getElementById('hist-search-input').value.toLowerCase();
    const rows = document.querySelectorAll('#hist-table-body tr');
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
    });
}

async function deleteSingleDonation(id) {
    if (!confirm(`คุณต้องการลบรายการโดเนท ID #${id} ใช่หรือไม่?`)) return;
    try {
        const res = await fetch(`/api/admin/donations/${encodeURIComponent(id)}?token=${token}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            showToast(`🗑️ ลบรายการ ID #${id} สำเร็จแล้ว`);
            loadDonationHistory();
        } else {
            showToast(`❌ ลบล้มเหลว: ${data.error}`);
        }
    } catch(e) {
        showToast(`❌ ลบล้มเหลว: ${e.message}`);
    }
}

async function confirmClearHistory() {
    if (!confirm("⚠️ คุณแน่ใจหรือไม่ว่าต้องการลบประวัติการโดเนททั้งหมดออกจากฐานข้อมูล?")) return;
    try {
        const res = await fetch(`/api/admin/donations/clear?token=${token}`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast("🧹 ล้างประวัติการโดเนททั้งหมดสำเร็จแล้ว");
            loadDonationHistory();
        } else {
            showToast(`❌ ลบล้มเหลว: ${data.error}`);
        }
    } catch(e) {
        showToast(`❌ ลบล้มเหลว: ${e.message}`);
    }
}

function switchSubTab(subName) {
    document.querySelectorAll('.sub-tab-btn').forEach(btn => {
        btn.style.background = 'rgba(255, 255, 255, 0.05)';
        btn.style.color = 'var(--text-muted)';
        btn.classList.remove('active');
    });
    document.querySelectorAll('.subtab-content').forEach(c => c.style.display = 'none');

    const activeBtn = document.getElementById(`btn-subtab-${subName}`);
    const activeContent = document.getElementById(`subtab-${subName}`);
    if (activeBtn && activeContent) {
        activeBtn.classList.add('active');
        activeBtn.style.background = 'rgba(167, 139, 250, 0.15)';
        activeBtn.style.color = '#c4b5fd';
        activeContent.style.display = 'block';
    }
}

function updateGoalUrl() {
    const titleEl = document.getElementById('goal-cfg-title') || document.getElementById('goal-title-input');
    const targetEl = document.getElementById('goal-cfg-target') || document.getElementById('goal-target-input');
    const title = titleEl ? titleEl.value : "เป้าหมายสนับสนุนสตรีมเมอร์";
    const target = targetEl ? targetEl.value : "5000";
    const goalInput = document.getElementById('url-widget-goal');
    if (goalInput) {
        goalInput.value = `${window.location.origin}/widget/goal?token=${token}&title=${encodeURIComponent(title)}&target=${target}`;
    }
}

function copyWidgetUrl(id) {
    const input = document.getElementById(id);
    input.select();
    navigator.clipboard.writeText(input.value);
    alert('📋 คัดลอกลิงก์ Widget สำหรับ OBS สำเร็จแล้ว!');
}

async function loadMediaLists(selectedImage = null, selectedSound = null) {
    try {
        const res = await fetch(`/api/admin/media_list?token=${token}`);
        const data = await res.json();
        if (data.error) return;

        // 1. Populate Image Dropdown
        const imgSelect = document.getElementById('cfg-image-select');
        imgSelect.innerHTML = '';

        const presetImgGroup = document.createElement('optgroup');
        presetImgGroup.label = "✨ รูปภาพมาตรฐาน (Built-in Presets)";
        data.preset_images.forEach(img => {
            const opt = document.createElement('option');
            opt.value = img.url;
            opt.textContent = img.name;
            presetImgGroup.appendChild(opt);
        });
        imgSelect.appendChild(presetImgGroup);

        if (data.uploaded_images && data.uploaded_images.length > 0) {
            const uploadImgGroup = document.createElement('optgroup');
            uploadImgGroup.label = "📁 รูปภาพที่คุณอัปโหลด (Uploaded Images)";
            data.uploaded_images.forEach(img => {
                const opt = document.createElement('option');
                opt.value = img.url;
                opt.textContent = img.name;
                uploadImgGroup.appendChild(opt);
            });
            imgSelect.appendChild(uploadImgGroup);
        }

        // 2. Populate Sound Dropdown
        const sndSelect = document.getElementById('cfg-sound-select');
        sndSelect.innerHTML = '';

        const presetSndGroup = document.createElement('optgroup');
        presetSndGroup.label = "✨ เสียงเตือนมาตรฐาน (Built-in Presets)";
        data.preset_sounds.forEach(snd => {
            const opt = document.createElement('option');
            opt.value = snd.url;
            opt.textContent = snd.name;
            presetSndGroup.appendChild(opt);
        });
        sndSelect.appendChild(presetSndGroup);

        if (data.uploaded_sounds && data.uploaded_sounds.length > 0) {
            const uploadSndGroup = document.createElement('optgroup');
            uploadSndGroup.label = "📁 เสียงที่คุณอัปโหลด (Uploaded Sounds)";
            data.uploaded_sounds.forEach(snd => {
                const opt = document.createElement('option');
                opt.value = snd.url;
                opt.textContent = snd.name;
                uploadSndGroup.appendChild(opt);
            });
            sndSelect.appendChild(uploadSndGroup);
        }

        const noSoundOpt = document.createElement('option');
        noSoundOpt.value = "none";
        noSoundOpt.textContent = "🚫 ปิดเสียงเตือน";
        sndSelect.appendChild(noSoundOpt);

        // Set Selected Values
        const currentImgUrl = selectedImage || document.getElementById('cfg-image-url').value;
        if (currentImgUrl) {
            imgSelect.value = currentImgUrl;
            document.getElementById('cfg-image-url').value = currentImgUrl;
        }

        const currentSndUrl = selectedSound || document.getElementById('cfg-sound-effect').value;
        if (currentSndUrl) {
            sndSelect.value = currentSndUrl;
            document.getElementById('cfg-sound-effect').value = currentSndUrl;
        }

        updateLivePreview();
    } catch(e) {
        console.error("Failed to load media list:", e);
    }
}

function onMediaSelectChange(type) {
    if (type === 'image') {
        const val = document.getElementById('cfg-image-select').value;
        document.getElementById('cfg-image-url').value = val;
        updateLivePreview();
    } else if (type === 'sound') {
        const val = document.getElementById('cfg-sound-select').value;
        document.getElementById('cfg-sound-effect').value = val;
    }
}

async function uploadSelectedMedia(type) {
    const fileInput = type === 'image' ? document.getElementById('file-upload-image') : document.getElementById('file-upload-sound');
    if (!fileInput.files || fileInput.files.length === 0) return;

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', type);

    try {
        const res = await fetch(`/api/admin/upload_media?token=${token}`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.success) {
            alert(`✅ อัปโหลดไฟล์ ${type === 'image' ? 'รูปภาพ' : 'เสียง'} สำเร็จแล้ว!`);
            if (type === 'image') {
                await loadMediaLists(data.url, null);
            } else {
                await loadMediaLists(null, data.url);
            }
        } else {
            alert(`❌ การอัปโหลดล้มเหลว: ${data.error}`);
        }
    } catch(e) {
        alert(`❌ เกิดข้อผิดพลาดในการอัปโหลด: ${e.message}`);
    }
    fileInput.value = '';
}

function playSelectedSoundPreview() {
    return new Promise((resolve) => {
        const soundUrl = document.getElementById('cfg-sound-effect').value;
        const volume = (document.getElementById('cfg-sound-volume').value || 80) / 100;

        if (!soundUrl || soundUrl === 'none') {
            resolve(0);
            return;
        }

        try {
            const audio = new Audio(soundUrl);
            audio.volume = volume;

            let resolved = false;
            const finish = () => {
                if (!resolved) {
                    resolved = true;
                    const dur = (audio.duration && !isNaN(audio.duration)) ? audio.duration * 1000 : 1500;
                    resolve(dur);
                }
            };

            audio.onended = finish;
            audio.onerror = () => {
                if (!resolved) {
                    resolved = true;
                    resolve(1500);
                }
            };

            audio.play().then(() => {
                setTimeout(finish, (audio.duration && !isNaN(audio.duration)) ? audio.duration * 1000 : 2000);
            }).catch(e => {
                console.error("Play sound error:", e);
                resolve(1500);
            });
        } catch(e) {
            resolve(1500);
        }
    });
}

function updateLivePreview() {
    const colorName = document.getElementById('cfg-color-name').value || '#fbbf24';
    const colorAmount = document.getElementById('cfg-color-amount').value || '#34d399';
    const colorMessage = document.getElementById('cfg-color-message').value || '#ffffff';
    const imageUrl = document.getElementById('cfg-image-url').value;
    const imagePos = document.getElementById('cfg-image-position').value || 'top';
    const templateText = document.getElementById('cfg-template-text').value || '{name} สนับสนุน {amount} บาท!';
    const fontFamily = document.getElementById('cfg-font-family').value || 'Prompt';
    const fontSize = document.getElementById('cfg-font-size').value || '32';

    const outerContainer = document.getElementById('preview-outer-container');
    const titleRow = document.getElementById('preview-title-row');
    const msgRow = document.getElementById('preview-msg-row');
    const previewImg = document.getElementById('preview-img');

    if (outerContainer && previewImg) {
        if (imagePos === 'none' || !imageUrl) {
            previewImg.style.display = 'none';
        } else {
            previewImg.style.display = 'block';
            previewImg.src = imageUrl;
            if (imagePos === 'top') {
                outerContainer.style.flexDirection = 'column';
            } else if (imagePos === 'bottom') {
                outerContainer.style.flexDirection = 'column-reverse';
            } else if (imagePos === 'left') {
                outerContainer.style.flexDirection = 'row';
            }
        }
    }

    if (titleRow) {
        titleRow.style.fontFamily = `'${fontFamily}', sans-serif`;
        titleRow.style.fontSize = `${fontSize}px`;
        titleRow.style.color = colorName;
        
        let amountText = "5,000";
        let formattedAmountSpan = `<span style="color:${colorAmount};">฿${amountText}</span>`;
        let text = templateText.replace('{name}', 'Test USER').replace('{amount}', formattedAmountSpan);
        text = text.replace(`฿${formattedAmountSpan}`, formattedAmountSpan);
        
        titleRow.innerHTML = text;
    }

    if (msgRow) {
        msgRow.style.fontFamily = `'${fontFamily}', sans-serif`;
        msgRow.style.color = colorMessage;
    }
}

function updateTopPreview() {
    const colorName = document.getElementById('top-cfg-color-name').value || '#ffffff';
    const colorAmount = document.getElementById('top-cfg-color-amount').value || '#fbbf24';
    const fontName = document.getElementById('top-cfg-font-name').value || 'Prompt';
    const fontAmount = document.getElementById('top-cfg-font-amount').value || 'Prompt';
    const fontSizeName = document.getElementById('top-cfg-font-size-name').value || '28';
    const fontSizeAmount = document.getElementById('top-cfg-font-size-amount').value || '28';
    const itemGap = document.getElementById('top-cfg-item-gap').value || '15';
    
    let layoutMode = 'name_first';
    const layoutRadios = document.getElementsByName('top-layout-mode');
    for (const radio of layoutRadios) {
        if (radio.checked) {
            layoutMode = radio.value;
            break;
        }
    }

    ['name_first', 'amount_first', 'name_top', 'amount_top'].forEach(mode => {
        const card = document.getElementById(`card-layout-${mode}`);
        if (card) {
            if (mode === layoutMode) {
                card.style.borderColor = '#fbbf24';
                card.style.background = 'rgba(251, 191, 36, 0.15)';
            } else {
                card.style.borderColor = 'transparent';
                card.style.background = 'rgba(255, 255, 255, 0.05)';
            }
        }
    });

    const box = document.getElementById('top-preview-box');
    const nameEl = document.getElementById('top-preview-name');
    const amountEl = document.getElementById('top-preview-amount');

    if (!box || !nameEl || !amountEl) return;

    box.style.gap = `${itemGap}px`;

    nameEl.style.color = colorName;
    nameEl.style.fontFamily = `'${fontName}', sans-serif`;
    nameEl.style.fontSize = `${fontSizeName}px`;

    amountEl.style.color = colorAmount;
    amountEl.style.fontFamily = `'${fontAmount}', sans-serif`;
    amountEl.style.fontSize = `${fontSizeAmount}px`;

    if (layoutMode === 'name_first') {
        box.style.flexDirection = 'row';
        box.style.alignItems = 'center';
        box.style.justifyContent = 'flex-start';
        nameEl.style.order = '1';
        amountEl.style.order = '2';
    } else if (layoutMode === 'amount_first') {
        box.style.flexDirection = 'row';
        box.style.alignItems = 'center';
        box.style.justifyContent = 'flex-start';
        nameEl.style.order = '2';
        amountEl.style.order = '1';
    } else if (layoutMode === 'name_top') {
        box.style.flexDirection = 'column';
        box.style.alignItems = 'center';
        box.style.justifyContent = 'flex-start';
        nameEl.style.order = '1';
        amountEl.style.order = '2';
    } else if (layoutMode === 'amount_top') {
        box.style.flexDirection = 'column';
        box.style.alignItems = 'center';
        box.style.justifyContent = 'flex-start';
        nameEl.style.order = '2';
        amountEl.style.order = '1';
    }
}

async function saveTopDonatorConfig() {
    let layoutMode = 'name_first';
    const layoutRadios = document.getElementsByName('top-layout-mode');
    for (const radio of layoutRadios) {
        if (radio.checked) {
            layoutMode = radio.value;
            break;
        }
    }

    const topConfig = {
        start_date: document.getElementById('top-cfg-start-date').value,
        color_name: document.getElementById('top-cfg-color-name').value,
        color_amount: document.getElementById('top-cfg-color-amount').value,
        font_family_name: document.getElementById('top-cfg-font-name').value,
        font_family_amount: document.getElementById('top-cfg-font-amount').value,
        font_size_name: parseInt(document.getElementById('top-cfg-font-size-name').value),
        font_size_amount: parseInt(document.getElementById('top-cfg-font-size-amount').value),
        item_gap: parseInt(document.getElementById('top-cfg-item-gap').value),
        layout_mode: layoutMode,
        limit: parseInt(document.getElementById('top-cfg-limit').value),
        filter_badwords: document.getElementById('top-cfg-filter-badwords').checked,
        custom_badwords: document.getElementById('top-cfg-custom-badwords').value
    };

    try {
        const res = await fetch(`/api/admin/config?token=${token}`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ top_donator_config: topConfig })
        });
        const data = await res.json();
        if (data.success) {
            showToast("💾 บันทึกการตั้งค่า Top Donator เรียบร้อยแล้ว!");
        } else {
            showToast(`❌ เกิดข้อผิดพลาด: ${data.error}`);
        }
    } catch(e) {
        showToast(`❌ บันทึกล้มเหลว: ${e.message}`);
    }
}

function updateRecentPreview() {
    const colorName = document.getElementById('recent-cfg-color-name').value || '#ffffff';
    const colorAmount = document.getElementById('recent-cfg-color-amount').value || '#34d399';
    const fontName = document.getElementById('recent-cfg-font-name').value || 'Prompt';
    const fontAmount = document.getElementById('recent-cfg-font-amount').value || 'Prompt';
    const fontSizeName = document.getElementById('recent-cfg-font-size-name').value || '28';
    const fontSizeAmount = document.getElementById('recent-cfg-font-size-amount').value || '28';
    const itemGap = document.getElementById('recent-cfg-item-gap').value || '15';
    
    let layoutMode = 'name_first';
    const layoutRadios = document.getElementsByName('recent-layout-mode');
    for (const radio of layoutRadios) {
        if (radio.checked) {
            layoutMode = radio.value;
            break;
        }
    }

    ['name_first', 'amount_first', 'name_top', 'amount_top'].forEach(mode => {
        const card = document.getElementById(`card-recent-layout-${mode}`);
        if (card) {
            if (mode === layoutMode) {
                card.style.borderColor = '#34d399';
                card.style.background = 'rgba(52, 211, 153, 0.15)';
            } else {
                card.style.borderColor = 'transparent';
                card.style.background = 'rgba(255, 255, 255, 0.05)';
            }
        }
    });

    const box = document.getElementById('recent-preview-box');
    const nameEl = document.getElementById('recent-preview-name');
    const amountEl = document.getElementById('recent-preview-amount');

    if (!box || !nameEl || !amountEl) return;

    box.style.gap = `${itemGap}px`;

    nameEl.style.color = colorName;
    nameEl.style.fontFamily = `'${fontName}', sans-serif`;
    nameEl.style.fontSize = `${fontSizeName}px`;

    amountEl.style.color = colorAmount;
    amountEl.style.fontFamily = `'${fontAmount}', sans-serif`;
    amountEl.style.fontSize = `${fontSizeAmount}px`;

    if (layoutMode === 'name_first') {
        box.style.flexDirection = 'row';
        box.style.alignItems = 'center';
        box.style.justifyContent = 'flex-start';
        nameEl.style.order = '1';
        amountEl.style.order = '2';
    } else if (layoutMode === 'amount_first') {
        box.style.flexDirection = 'row';
        box.style.alignItems = 'center';
        box.style.justifyContent = 'flex-start';
        nameEl.style.order = '2';
        amountEl.style.order = '1';
    } else if (layoutMode === 'name_top') {
        box.style.flexDirection = 'column';
        box.style.alignItems = 'center';
        box.style.justifyContent = 'flex-start';
        nameEl.style.order = '1';
        amountEl.style.order = '2';
    } else if (layoutMode === 'amount_top') {
        box.style.flexDirection = 'column';
        box.style.alignItems = 'center';
        box.style.justifyContent = 'flex-start';
        nameEl.style.order = '2';
        amountEl.style.order = '1';
    }
}

async function saveRecentDonatorConfig() {
    let layoutMode = 'name_first';
    const layoutRadios = document.getElementsByName('recent-layout-mode');
    for (const radio of layoutRadios) {
        if (radio.checked) {
            layoutMode = radio.value;
            break;
        }
    }

    const recentConfig = {
        color_name: document.getElementById('recent-cfg-color-name').value,
        color_amount: document.getElementById('recent-cfg-color-amount').value,
        font_family_name: document.getElementById('recent-cfg-font-name').value,
        font_family_amount: document.getElementById('recent-cfg-font-amount').value,
        font_size_name: parseInt(document.getElementById('recent-cfg-font-size-name').value),
        font_size_amount: parseInt(document.getElementById('recent-cfg-font-size-amount').value),
        item_gap: parseInt(document.getElementById('recent-cfg-item-gap').value),
        layout_mode: layoutMode,
        limit: parseInt(document.getElementById('recent-cfg-limit').value),
        filter_badwords: document.getElementById('recent-cfg-filter-badwords').checked,
        custom_badwords: document.getElementById('recent-cfg-custom-badwords').value
    };

    try {
        const res = await fetch(`/api/admin/config?token=${token}`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ recent_donator_config: recentConfig })
        });
        const data = await res.json();
        if (data.success) {
            showToast("💾 บันทึกการตั้งค่า Recent Donator เรียบร้อยแล้ว!");
        } else {
            showToast(`❌ เกิดข้อผิดพลาด: ${data.error}`);
        }
    } catch(e) {
        showToast(`❌ บันทึกล้มเหลว: ${e.message}`);
    }
}

async function updateGoalPreview() {
    const title = document.getElementById('goal-cfg-title').value || 'เป้าหมายสนับสนุนสตรีมเมอร์';
    const targetAmount = parseFloat(document.getElementById('goal-cfg-target').value) || 5000;
    const initialAmount = parseFloat(document.getElementById('goal-cfg-initial').value) || 0;
    const colorBar = document.getElementById('goal-cfg-color-bar').value || '#22c55e';
    const colorBg = document.getElementById('goal-cfg-color-bg').value || '#1e293b';
    const colorText = document.getElementById('goal-cfg-color-text').value || '#ffffff';
    const fontTitle = document.getElementById('goal-cfg-font-title').value || 'Prompt';
    const fontNumber = document.getElementById('goal-cfg-font-number').value || 'Prompt';
    const fontSize = document.getElementById('goal-cfg-font-size').value || '22';

    let raised = 0;
    try {
        const res = await fetch(`/api/donations/goal`);
        if (res.ok) {
            const data = await res.json();
            raised = data.current_amount || initialAmount;
        }
    } catch(e) {
        raised = initialAmount;
    }

    const current = Math.max(initialAmount, raised);
    const percentage = Math.min(100, Math.max(0, (current / targetAmount) * 100)).toFixed(0);

    const barBg = document.getElementById('goal-preview-bar-bg');
    const barFill = document.getElementById('goal-preview-bar-fill');
    const textEl = document.getElementById('goal-preview-text');
    const startLbl = document.getElementById('goal-preview-start-lbl');
    const endLbl = document.getElementById('goal-preview-end-lbl');

    if (barBg) barBg.style.background = colorBg;
    if (barFill) {
        barFill.style.background = colorBar;
        barFill.style.width = `${percentage}%`;
    }
    if (textEl) {
        textEl.style.color = colorText;
        textEl.style.fontFamily = `'${fontTitle}', sans-serif`;
        textEl.style.fontSize = `${fontSize}px`;
        textEl.innerHTML = `${title} <span style="font-family: '${fontNumber}', sans-serif;">฿${Number(current).toLocaleString('th-TH', {minimumFractionDigits: 0})} (${percentage}%)</span>`;
    }
    if (startLbl) {
        startLbl.style.fontFamily = `'${fontNumber}', sans-serif`;
        startLbl.style.color = colorText;
        startLbl.textContent = `฿${Number(initialAmount).toLocaleString('th-TH', {minimumFractionDigits: 0})}`;
    }
    if (endLbl) {
        endLbl.style.fontFamily = `'${fontNumber}', sans-serif`;
        endLbl.style.color = colorText;
        endLbl.textContent = `฿${Number(targetAmount).toLocaleString('th-TH', {minimumFractionDigits: 0})}`;
    }
}

async function saveGoalConfig() {
    const goalConfig = {
        title: document.getElementById('goal-cfg-title').value,
        start_date: document.getElementById('goal-cfg-start-date').value,
        end_date: document.getElementById('goal-cfg-end-date').value,
        target_amount: parseFloat(document.getElementById('goal-cfg-target').value) || 5000,
        initial_amount: parseFloat(document.getElementById('goal-cfg-initial').value) || 0,
        color_bar: document.getElementById('goal-cfg-color-bar').value,
        color_bg: document.getElementById('goal-cfg-color-bg').value,
        color_text: document.getElementById('goal-cfg-color-text').value,
        font_family_title: document.getElementById('goal-cfg-font-title').value,
        font_family_number: document.getElementById('goal-cfg-font-number').value,
        font_size: parseInt(document.getElementById('goal-cfg-font-size').value) || 22
    };

    try {
        const res = await fetch(`/api/admin/config?token=${token}`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ goal_config: goalConfig })
        });
        const data = await res.json();
        if (data.success) {
            showToast("💾 บันทึกการตั้งค่า Donate Goal เรียบร้อยแล้ว!");
        } else {
            showToast(`❌ เกิดข้อผิดพลาด: ${data.error}`);
        }
    } catch(e) {
        showToast(`❌ บันทึกล้มเหลว: ${e.message}`);
    }
}

async function testTTSVoice() {
    const text = "ทดสอบระบบเสียงอ่านภาษาไทย ขอบคุณสำหรับการสนับสนุนครับ";
    const vol = document.getElementById('cfg-sound-volume') ? parseInt(document.getElementById('cfg-sound-volume').value) : 80;
    const voiceEl = document.getElementById('cfg-tts-voice');
    let voice = voiceEl ? voiceEl.value : 'th-TH-PremwadeeNeural';
    if (!voice || voice === 'default') voice = 'th-TH-PremwadeeNeural';

    try {
        const res = await fetch(`/api/tts?text=${encodeURIComponent(text)}&voice=${encodeURIComponent(voice)}`);
        const data = await res.json();
        if (data.success && data.audio_url) {
            const audio = new Audio(data.audio_url);
            audio.volume = Math.min(1.0, Math.max(0.0, vol / 100));
            audio.play().catch(e => console.error("Test TTS play error:", e));
            return;
        }
    } catch(e) {
        console.error("Edge TTS test failed, falling back to Web Speech:", e);
    }

    // Fallback
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "th-TH";
        utterance.volume = vol / 100;
        window.speechSynthesis.speak(utterance);
    }
}

async function triggerTestAlert(saveToDb = false) {
    // 1. Auto-save current config quietly first
    await saveAlertConfig(false);

    // 2. Play selected sound effect and wait for exact duration
    const soundDurationMs = await playSelectedSoundPreview();

    // 3. Play TTS AFTER sound finishes + 1 second delay (1000ms)
    if (document.getElementById('cfg-enable-tts').checked) {
        const delayMs = soundDurationMs > 0 ? (soundDurationMs + 1000) : 500;
        setTimeout(() => {
            testTTSVoice();
        }, delayMs);
    }

    // Animate preview box
    const box = document.getElementById('preview-alert-box');
    if (box) {
        box.style.transform = "scale(1.1)";
        setTimeout(() => {
            box.style.transform = "scale(1.0)";
        }, 400);
    }

    // Randomize name and amount (100 - 1000 THB)
    const sampleNames = [
        "สมชาย สายเปย์",
        "น้องมิว ใจดี",
        "พี่ตูน สั่งลุย",
        "นักซุ่มสายโดเนท",
        "ผู้ไม่ประสงค์ออกนาม",
        "เจ้าชายสายเปย์",
        "แมวส้มครองโลก",
        "คุณกิตติ รายงาน",
        "น้องปลาดาว",
        "สายเปย์ทรงพลัง",
        "FC ตัวจริง",
        "ผู้สนับสนุนใจดี",
        "คุณนายสายบุญ",
        "น้องส้มส้ม",
        "สตรีมเมอร์สู้ๆ"
    ];
    const randomName = sampleNames[Math.floor(Math.random() * sampleNames.length)];
    const randomAmount = Math.floor(Math.random() * 901) + 100; // 100 - 1000 THB

    // Send API call to broadcast fake alert to OBS overlay
    try {
        await fetch(`/api/admin/test_alert?token=${token}`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                name: randomName,
                message: "ตัวอย่าง Donate Alert",
                amount: randomAmount,
                save_to_db: saveToDb
            })
        });
        if (saveToDb) {
            showToast(`🧪 ทดสอบสลิปจำลอง (${randomName} ฿${randomAmount.toLocaleString()}) บันทึกประวัติแล้ว!`);
            // Refresh history table if active
            if (typeof loadDonationHistory === 'function') loadDonationHistory();
        } else {
            showToast(`🔔 ส่งสัญญาณทดสอบการแจ้งเตือน (${randomName} ฿${randomAmount.toLocaleString()}) สำเร็จ!`);
        }
    } catch(e) {
        console.error("Test alert error:", e);
    }
}

async function saveAlertConfig(showNotification = true) {
    const alertConfig = {
        color_name: document.getElementById('cfg-color-name').value,
        color_amount: document.getElementById('cfg-color-amount').value,
        color_message: document.getElementById('cfg-color-message').value,
        template_text: document.getElementById('cfg-template-text').value,
        image_url: document.getElementById('cfg-image-url').value,
        image_position: document.getElementById('cfg-image-position').value,
        font_family: document.getElementById('cfg-font-family').value,
        font_size: parseInt(document.getElementById('cfg-font-size').value),
        duration: parseInt(document.getElementById('cfg-duration').value),
        anim_in: document.getElementById('cfg-anim-in').value,
        anim_out: document.getElementById('cfg-anim-out').value,
        sound_effect: document.getElementById('cfg-sound-effect').value,
        sound_volume: parseInt(document.getElementById('cfg-sound-volume').value),
        enable_tts: document.getElementById('cfg-enable-tts').checked,
        tts_voice: document.getElementById('cfg-tts-voice') ? document.getElementById('cfg-tts-voice').value : 'th-TH-PremwadeeNeural',
        min_display: document.getElementById('cfg-min-display') ? parseFloat(document.getElementById('cfg-min-display').value) : 0
    };

    const payload = {
        streamer_name: document.getElementById('streamer-name') ? document.getElementById('streamer-name').value : '',
        promptpay_id: document.getElementById('promptpay-id').value,
        minimum_donation: parseFloat(document.getElementById('minimum-donation').value),
        line_window_title: document.getElementById('window-select').value,
        regex_formats: regexFormats,
        alert_config: alertConfig,
        token: token
    };

    try {
        const res = await fetch(`/api/admin/config`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            if (showNotification) showToast("💾 บันทึกการตั้งค่า Alert เรียบร้อยแล้ว!");
        } else {
            showToast("❌ บันทึกไม่สำเร็จ: " + data.error);
        }
    } catch (e) {
        showToast("❌ เกิดข้อผิดพลาดในการบันทึก: " + e.message);
    }
}

function openWidgetPreview(type) {
    let url = '';
    if (type === 'alert') url = document.getElementById('url-widget-alert').value;
    else if (type === 'top') url = document.getElementById('url-widget-top').value;
    else if (type === 'recent') url = document.getElementById('url-widget-recent').value;
    else if (type === 'goal') url = document.getElementById('url-widget-goal').value;
    if (url) window.open(url, '_blank');
}

function runLiveTest(text) {
    const resultDiv = document.getElementById('test-result');
    if (!resultDiv) return;
    
    if (!text) {
        resultDiv.innerHTML = "";
        resultDiv.style.display = 'none';
        return;
    }

    resultDiv.style.display = 'block';
    const flatText = text.replace(/\n/g, "").replace(/ /g, "");

    const regexCards = document.querySelectorAll('.regex-card');
    let foundMatch = null;
    
    for (let card of regexCards) {
        const idx = card.dataset.index;
        const name = document.getElementById(`regex-name-${idx}`).value || `รูปแบบที่ ${parseInt(idx) + 1}`;
        const pattern = document.getElementById(`regex-pattern-${idx}`).value;
        const type = document.getElementById(`regex-type-${idx}`).value;
        
        if (!pattern) continue;
        
        try {
            const regex = new RegExp(pattern);
            const match = flatText.match(regex);
            
            if (match && match[1]) {
                foundMatch = {
                    name: name,
                    amount: match[1].replace(/,/g, ''),
                    type: type
                };
                break;
            }
        } catch(e) {
            // Invalid regex syntax
        }
    }
    
    if (foundMatch) {
        resultDiv.innerHTML = `
            <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 12px; padding: 20px; text-align: center; margin-top: 20px;">
                <div style="color: #10b981; font-weight: bold; font-size: 1.3rem; margin-bottom: 8px;">
                    <i class="fa-solid fa-circle-check"></i> ค้นพบยอดเงินแล้ว <span style="font-size: 1.8rem; color: #34d399; font-weight: 800;">${foundMatch.amount}</span> บาท
                </div>
                <div style="font-size: 1.1rem; color: #e2e8f0;">
                    ตรงกับรูปแบบของ: <strong style="color: #a78bfa; background: rgba(167, 139, 250, 0.2); padding: 4px 12px; border-radius: 8px; border: 1px solid rgba(167, 139, 250, 0.4);">${foundMatch.name}</strong>
                </div>
            </div>
        `;
    } else {
        resultDiv.innerHTML = `
            <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 12px; padding: 20px; text-align: center; margin-top: 20px;">
                <div style="color: #ef4444; font-weight: bold; font-size: 1.1rem; margin-bottom: 12px;">
                    <i class="fa-solid fa-circle-xmark"></i> ไม่พบยอดเงิน หรือข้อความไม่ตรงกับรูปแบบธนาคารใดเลย
                </div>
                <button class="btn" style="background: var(--primary); padding: 10px 20px; font-size: 0.95rem; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);" onclick="createNewPatternFromOCR()">
                    <i class="fa-solid fa-wand-magic-sparkles"></i> ✨ สร้างรูปแบบรับเงินทันที
                </button>
            </div>
        `;
    }
}

// Test OCR
async function testOCR() {
    const btn = document.getElementById('btn-test-ocr');
    const resultDiv = document.getElementById('ocr-result');
    const windowTitle = document.getElementById('window-select').value;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> กำลังอ่านข้อความ...';
    resultDiv.style.display = 'block';
    resultDiv.textContent = "กำลังแคปเจอร์และอ่านข้อความจากหน้าต่างที่เลือก (ใช้เวลา 1-3 วินาที)...";
    
    lastFetchedOCRText = "";
    runLiveTest(null);

    try {
        const res = await fetch(`/api/admin/test_ocr?token=${token}`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ window_title: windowTitle })
        });
        const data = await res.json();
        
        if (data.success) {
            lastFetchedOCRText = data.text;
            resultDiv.textContent = ">> ข้อความที่อ่านได้ล่าสุด:\n\n" + data.text;
            resultDiv.style.color = "#10b981";
            runLiveTest(data.text);
        } else {
            resultDiv.textContent = "❌ เกิดข้อผิดพลาด:\n\n" + data.error;
            resultDiv.style.color = "#ef4444";
            runLiveTest(null);
        }
    } catch (e) {
        resultDiv.textContent = "❌ การเชื่อมต่อล้มเหลว:\n\n" + e.message;
        resultDiv.style.color = "#ef4444";
        runLiveTest(null);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-eye"></i> ทดสอบอ่านข้อความล่าสุด';
    }
}

function openDonatePage() {
    window.open('/', '_blank');
}

function showToast(msg = "💾 บันทึกการตั้งค่าสำเร็จ!") {
    const toast = document.getElementById('toast');
    if (msg) toast.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${msg}`;
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

async function fetchTunnelStatus() {
    try {
        const res = await fetch(`/api/admin/tunnel/status?token=${token}`);
        if (!res.ok) return;
        const data = await res.json();

        const badge = document.getElementById('tunnel-status-badge');
        const urlInput = document.getElementById('public-donate-url');

        if (data.status === 'connected' && data.donate_url) {
            badge.style.background = 'rgba(52, 211, 153, 0.2)';
            badge.style.color = '#6ee7b7';
            badge.style.borderColor = 'rgba(52, 211, 153, 0.4)';
            badge.innerHTML = '🟢 ออนไลน์ (Public Tunnel Active)';
            urlInput.value = data.donate_url;

            // Auto-refresh config if Mode 2 is active but synced_slug isn't populated yet
            if (currentNetworkMode === 2 && !window.__VELOX_URL__) {
                loadConfig();
            }
        } else if (data.status === 'connecting') {
            badge.style.background = 'rgba(234, 179, 8, 0.2)';
            badge.style.color = '#fde047';
            badge.style.borderColor = 'rgba(234, 179, 8, 0.4)';
            badge.innerHTML = '🟡 กำลังสร้างอุโมงค์เชื่อมต่อ...';
            urlInput.value = 'กำลังสร้างลิงก์สาธารณะ...';
        } else {
            badge.style.background = 'rgba(239, 68, 68, 0.2)';
            badge.style.color = '#fca5a5';
            badge.style.borderColor = 'rgba(239, 68, 68, 0.4)';
            badge.innerHTML = '🔴 ออฟไลน์';
            urlInput.value = data.error_message || 'ไม่ได้เปิดใช้อุโมงค์สาธารณะ';
        }
    } catch(e) {
        console.error("Fetch tunnel status error:", e);
    }
}

function copyPublicDonateUrl() {
    const input = document.getElementById('public-donate-url');
    if (!input.value || input.value.includes('กำลัง') || input.value.includes('ไม่ได้เปิด')) {
        showToast("❌ ยังไม่มีลิงก์สาธารณะ กรุณารออุโมงค์เชื่อมต่อสักครู่");
        return;
    }
    input.select();
    navigator.clipboard.writeText(input.value);
    showToast("📋 คัดลอกลิงก์รับโดเนทสาธารณะ Cloudflare สำเร็จแล้ว!");
}

function openPublicDonateUrl() {
    const input = document.getElementById('public-donate-url');
    if (input.value && input.value.startsWith('http')) {
        window.open(input.value, '_blank');
    } else {
        showToast("❌ ลิงก์ยังไม่พร้อมใช้งาน");
    }
}

function openGuideModal() {
    const modal = document.getElementById('guide-modal');
    if (modal) modal.classList.add('show');
}

function closeGuideModal() {
    const modal = document.getElementById('guide-modal');
    if (modal) modal.classList.remove('show');
}

async function checkForSoftwareUpdate(showToastIfLatest = false) {
    try {
        const res = await fetch(`/api/admin/check_update?token=${token}`);
        if (!res.ok) return;
        const data = await res.json();
        
        const curVerEl = document.getElementById('setting-current-ver-text');
        const badgeEl = document.getElementById('setting-update-status-badge');
        
        if (curVerEl) curVerEl.textContent = `v${data.current_version || '1.0.0'}`;
        
        if (data.has_update) {
            if (badgeEl) {
                badgeEl.innerHTML = `🚀 มีเวอร์ชันใหม่ (v${data.latest_version})`;
                badgeEl.style.background = 'rgba(245, 158, 11, 0.2)';
                badgeEl.style.color = '#fbbf24';
                badgeEl.style.border = '1px solid rgba(245, 158, 11, 0.4)';
            }

            const modal = document.getElementById('update-modal');
            const vTag = document.getElementById('update-version-tag');
            const curTag = document.getElementById('update-current-tag');
            const notesText = document.getElementById('update-notes-text');
            
            if (vTag) vTag.textContent = `v${data.latest_version}`;
            if (curTag) curTag.textContent = `v${data.current_version}`;
            if (notesText) notesText.innerHTML = escapeHtml(data.release_notes || "ปรับปรุงประสิทธิภาพและความเสถียรของระบบ");
            
            // Reset modal state views
            const infoState = document.getElementById('update-info-state');
            const progressState = document.getElementById('update-progress-state');
            if (infoState) infoState.style.display = 'block';
            if (progressState) progressState.style.display = 'none';

            if (modal) modal.classList.add('show');
            window.__LATEST_UPDATE_VER__ = data.latest_version;
            window.__UPDATE_DOWNLOAD_URL__ = data.download_url;
        } else {
            if (badgeEl) {
                badgeEl.innerHTML = `🟢 เป็นเวอร์ชันล่าสุด`;
                badgeEl.style.background = 'rgba(52, 211, 153, 0.2)';
                badgeEl.style.color = '#34d399';
                badgeEl.style.border = '1px solid rgba(52, 211, 153, 0.3)';
            }
            if (showToastIfLatest) {
                showToast(`🟢 โปรแกรมของคุณเป็นเวอร์ชันล่าสุดเรียบร้อยแล้ว (v${data.current_version})`);
            }
        }
    } catch(e) {
        console.error("Check update error:", e);
        if (showToastIfLatest) showToast("❌ ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์อัปเดตได้");
    }
}

function manualCheckUpdateBtn() {
    checkForSoftwareUpdate(true);
}

let updatePollInterval = null;

async function startAutoUpdateProcess() {
    const downloadUrl = window.__UPDATE_DOWNLOAD_URL__ || "https://github.com/devwangu/veloxdonate/releases/download/v1.0.0/VeloxDonate_v1.0.0.zip";
    
    // Switch modal view to progress state
    const infoState = document.getElementById('update-info-state');
    const progressState = document.getElementById('update-progress-state');
    if (infoState) infoState.style.display = 'none';
    if (progressState) progressState.style.display = 'block';

    try {
        const res = await fetch(`/api/admin/perform_update?token=${token}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ download_url: downloadUrl })
        });
        if (!res.ok) throw new Error("ไม่สามารถเริ่มต้นการอัปเดตได้");
        
        // Start polling progress
        updatePollInterval = setInterval(pollUpdateProgress, 600);
    } catch(e) {
        const msgText = document.getElementById('update-progress-msg');
        if (msgText) {
            msgText.textContent = `เกิดข้อผิดพลาด: ${e.message}`;
            msgText.style.color = '#f87171';
        }
    }
}

async function pollUpdateProgress() {
    try {
        const res = await fetch(`/api/admin/update_progress?token=${token}`);
        if (!res.ok) return;
        const data = await res.json();

        const bar = document.getElementById('update-progress-bar');
        const percentText = document.getElementById('update-percent-text');
        const msgText = document.getElementById('update-progress-msg');

        if (bar) bar.style.width = `${data.progress || 0}%`;
        if (percentText) percentText.textContent = `${data.progress || 0}%`;
        if (msgText && data.message) msgText.textContent = data.message;

        if (data.status === 'completed') {
            clearInterval(updatePollInterval);
            if (msgText) {
                msgText.textContent = "✅ ติดตั้งเวอร์ชันใหม่เรียบร้อยแล้ว! กำลังรีสตาร์ตแอปพลิเคชัน...";
                msgText.style.color = "#34d399";
            }
            setTimeout(() => {
                window.location.reload();
            }, 3500);
        } else if (data.status === 'error') {
            clearInterval(updatePollInterval);
            if (msgText) {
                msgText.textContent = `❌ ${data.message || data.error}`;
                msgText.style.color = "#f87171";
            }
        }
    } catch(e) {
        console.log("Polling update status...", e);
    }
}

function closeUpdateModal() {
    const modal = document.getElementById('update-modal');
    if (modal) modal.classList.remove('show');
    if (window.__LATEST_UPDATE_VER__) {
        localStorage.setItem('dismissed_update_version', window.__LATEST_UPDATE_VER__);
    }
}

document.addEventListener('click', (e) => {
    const guideModal = document.getElementById('guide-modal');
    if (guideModal && e.target === guideModal) {
        closeGuideModal();
    }
    const updateModal = document.getElementById('update-modal');
    if (updateModal && e.target === updateModal) {
        closeUpdateModal();
    }
    const autoGenModal = document.getElementById('auto-gen-modal');
    if (autoGenModal && e.target === autoGenModal) {
        closeAutoGenerateModal();
    }
});

// Init
function initDashboard() {
    restoreLastActiveTab();
    if (token) {
        loadConfig();
        fetchTunnelStatus();
        checkForSoftwareUpdate();
        setInterval(fetchTunnelStatus, 3000);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}

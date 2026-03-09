const API_URL = 'http://localhost:8000/api';
const WS_URL = 'ws://localhost:8000/ws';

// 全局配置 - 可以自己修改
const CONFIG = {
    ADMIN_NAME: 'admin',  // 管理员显示名称
    NORMAL_USER_NAME: '普通用户'  // 普通用户显示名称
};

let currentUser = null;
let token = null;
let websocket = null;

// 初始化
window.onload = function() {
    const savedToken = localStorage.getItem('token');
    if (savedToken) {
        token = savedToken;
        checkAuth();
    }
};

// 连接 WebSocket
function connectWebSocket() {
    websocket = new WebSocket(WS_URL);
    
    websocket.onopen = function() {
        console.log('WebSocket 已连接');
    };
    
    websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === 'new_message') {
            // 收到新消息，刷新消息列表
            loadMessages();
        }
    };
    
    websocket.onclose = function() {
        console.log('WebSocket 已断开，3秒后重连...');
        setTimeout(connectWebSocket, 3000);
    };
    
    websocket.onerror = function(error) {
        console.error('WebSocket 错误:', error);
    };
}

// 断开 WebSocket
function disconnectWebSocket() {
    if (websocket) {
        websocket.close();
        websocket = null;
    }
}

// 切换登录/注册标签
function switchTab(tab) {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const tabs = document.querySelectorAll('.auth-tab');
    
    tabs.forEach(t => t.classList.remove('active'));
    
    if (tab === 'login') {
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
        tabs[0].classList.add('active');
    } else {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
        tabs[1].classList.add('active');
    }
    
    document.getElementById('authError').textContent = '';
}

// 登录
async function login() {
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;
    
    if (!username || !password) {
        showAuthError('请输入用户名和密码');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            token = data.token;
            currentUser = data.user;
            localStorage.setItem('token', token);
            showChatApp();
        } else {
            showAuthError(data.detail || '登录失败');
        }
    } catch (error) {
        showAuthError('网络错误，请检查后端是否运行');
    }
}

// 注册
async function register() {
    const username = document.getElementById('registerUsername').value.trim();
    const password = document.getElementById('registerPassword').value;
    
    if (!username || !password) {
        showAuthError('请输入用户名和密码');
        return;
    }
    
    if (password.length < 6) {
        showAuthError('密码至少6位');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            token = data.token;
            currentUser = data.user;
            localStorage.setItem('token', token);
            showChatApp();
        } else {
            showAuthError(data.detail || '注册失败');
        }
    } catch (error) {
        showAuthError('网络错误，请检查后端是否运行');
    }
}

// 检查认证状态
async function checkAuth() {
    try {
        const response = await fetch(`${API_URL}/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            currentUser = await response.json();
            showChatApp();
        } else {
            logout();
        }
    } catch (error) {
        logout();
    }
}

// 显示聊天界面
function showChatApp() {
    document.getElementById('authContainer').style.display = 'none';
    document.getElementById('chatApp').style.display = 'flex';
    
    document.getElementById('userName').textContent = currentUser.username;
    document.getElementById('userRole').textContent = currentUser.is_admin ? CONFIG.ADMIN_NAME : CONFIG.NORMAL_USER_NAME;
    
    // 设置头像
    const avatarUrl = currentUser.avatar ? `http://localhost:8000${currentUser.avatar}` : 'http://localhost:8000/uploads/avatars/default.png';
    const avatarElement = document.getElementById('userAvatar');
    avatarElement.src = avatarUrl;
    
    // 如果是管理员，添加彩色边框
    if (currentUser.is_admin) {
        avatarElement.classList.add('admin-avatar-header');
    } else {
        avatarElement.classList.remove('admin-avatar-header');
    }
    
    loadMessages();
    connectWebSocket();
}

// 退出登录
function logout() {
    disconnectWebSocket();
    token = null;
    currentUser = null;
    localStorage.removeItem('token');
    
    document.getElementById('authContainer').style.display = 'flex';
    document.getElementById('chatApp').style.display = 'none';
    document.getElementById('chatContainer').innerHTML = '';
}

// 显示认证错误
function showAuthError(message) {
    document.getElementById('authError').textContent = message;
}

// 加载消息
async function loadMessages() {
    try {
        const response = await fetch(`${API_URL}/messages`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (response.ok) {
            const messages = await response.json();
            displayMessages(messages);
        }
    } catch (error) {
        console.error('加载消息失败:', error);
    }
}

// 显示消息
function displayMessages(messages) {
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.innerHTML = '';
    
    messages.forEach(msg => {
        const isCurrentUser = msg.user_id === currentUser.id;
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isCurrentUser ? 'fan-message' : 'idol-message'}`;
        
        const time = formatMessageTime(msg.created_at);
        const roleTag = msg.is_admin ? `<span class="admin-tag">${CONFIG.ADMIN_NAME}</span>` : '';
        const avatarUrl = msg.avatar ? `http://localhost:8000${msg.avatar}` : 'http://localhost:8000/uploads/avatars/default.png';
        const avatarClass = msg.is_admin ? 'message-avatar admin-avatar' : 'message-avatar';
        
        // 根据消息类型生成内容
        let messageContent = '';
        if (msg.message_type === 'image') {
            messageContent = `
                ${msg.content ? `<div>${escapeHtml(msg.content)}</div>` : ''}
                <img src="http://localhost:8000${msg.media_url}" alt="图片" onclick="window.open('http://localhost:8000${msg.media_url}', '_blank')">
            `;
        } else if (msg.message_type === 'video') {
            messageContent = `
                ${msg.content ? `<div>${escapeHtml(msg.content)}</div>` : ''}
                <video controls>
                    <source src="http://localhost:8000${msg.media_url}" type="video/mp4">
                </video>
            `;
        } else {
            messageContent = escapeHtml(msg.content);
        }
        
        messageDiv.innerHTML = `
            <img src="${avatarUrl}" alt="头像" class="${avatarClass}">
            <div class="message-content">
                <div class="message-header">
                    ${roleTag}
                    <span class="message-username">${escapeHtml(msg.username)}</span>
                </div>
                <div class="message-bubble">${messageContent}</div>
                <span class="message-time">${time}</span>
            </div>
        `;
        
        chatContainer.appendChild(messageDiv);
    });
    
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// 发送消息
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const content = input.value.trim();
    
    if (!content) return;
    
    try {
        const response = await fetch(`${API_URL}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ content })
        });
        
        if (response.ok) {
            input.value = '';
            // WebSocket 会自动推送新消息，不需要手动刷新
        }
    } catch (error) {
        console.error('发送消息失败:', error);
    }
}

// 移除不需要的函数
function refreshMessages() {
    loadMessages();
}

// 这些函数已不需要
function startMessagePolling() {}
function stopMessagePolling() {}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 回车发送消息
document.addEventListener('DOMContentLoaded', function() {
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
});

// 上传头像
async function uploadAvatar() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`${API_URL}/upload-avatar`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });
            
            if (response.ok) {
                const data = await response.json();
                // 更新头像显示
                document.getElementById('userAvatar').src = `http://localhost:8000${data.avatar}`;
                currentUser.avatar = data.avatar;
                alert('头像上传成功！');
                loadMessages(); // 刷新消息列表以显示新头像
            } else {
                alert('头像上传失败');
            }
        } catch (error) {
            console.error('上传头像失败:', error);
            alert('头像上传失败');
        }
    };
    
    input.click();
}

// 修改用户名
async function changeUsername() {
    const newUsername = prompt('请输入新的用户名:', currentUser.username);
    
    if (!newUsername || newUsername.trim() === '') {
        return;
    }
    
    if (newUsername === currentUser.username) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/update-username?new_username=${encodeURIComponent(newUsername)}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            currentUser.username = data.username;
            document.getElementById('userName').textContent = data.username;
            alert('用户名修改成功！');
            loadMessages(); // 刷新消息列表
        } else {
            const error = await response.json();
            alert(error.detail || '用户名修改失败');
        }
    } catch (error) {
        console.error('修改用户名失败:', error);
        alert('修改用户名失败');
    }
}

// 格式化时间显示
function formatMessageTime(dateTimeStr) {
    const msgDate = new Date(dateTimeStr);
    const now = new Date();
    
    // 计算时间差（毫秒）
    const diffMs = now - msgDate;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    // 今天：显示时分
    if (diffDays === 0 && msgDate.getDate() === now.getDate()) {
        const hours = String(msgDate.getHours()).padStart(2, '0');
        const minutes = String(msgDate.getMinutes()).padStart(2, '0');
        return `${hours}:${minutes}`;
    }
    
    // 昨天
    if (diffDays === 1 || (diffDays === 0 && msgDate.getDate() !== now.getDate())) {
        const hours = String(msgDate.getHours()).padStart(2, '0');
        const minutes = String(msgDate.getMinutes()).padStart(2, '0');
        return `昨天 ${hours}:${minutes}`;
    }
    
    // 一周内：显示星期几
    if (diffDays < 7) {
        const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
        const weekday = weekdays[msgDate.getDay()];
        const hours = String(msgDate.getHours()).padStart(2, '0');
        const minutes = String(msgDate.getMinutes()).padStart(2, '0');
        return `${weekday} ${hours}:${minutes}`;
    }
    
    // 今年：显示月日
    if (msgDate.getFullYear() === now.getFullYear()) {
        const month = msgDate.getMonth() + 1;
        const day = msgDate.getDate();
        const hours = String(msgDate.getHours()).padStart(2, '0');
        const minutes = String(msgDate.getMinutes()).padStart(2, '0');
        return `${month}月${day}日 ${hours}:${minutes}`;
    }
    
    // 去年及更早：显示年月日
    const year = msgDate.getFullYear();
    const month = msgDate.getMonth() + 1;
    const day = msgDate.getDate();
    const hours = String(msgDate.getHours()).padStart(2, '0');
    const minutes = String(msgDate.getMinutes()).padStart(2, '0');
    return `${year}年${month}月${day}日 ${hours}:${minutes}`;
}

// 选择媒体文件
async function selectMedia() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*,video/*';
    
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        // 显示上传中提示
        const messageInput = document.getElementById('messageInput');
        const originalPlaceholder = messageInput.placeholder;
        messageInput.placeholder = '正在上传...';
        messageInput.disabled = true;
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`${API_URL}/upload-media`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });
            
            if (response.ok) {
                const data = await response.json();
                
                // 发送消息
                const content = messageInput.value.trim() || '';
                await fetch(`${API_URL}/messages`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        content: content,
                        message_type: data.media_type,
                        media_url: data.media_url
                    })
                });
                
                messageInput.value = '';
            } else {
                alert('上传失败');
            }
        } catch (error) {
            console.error('上传失败:', error);
            alert('上传失败');
        } finally {
            messageInput.placeholder = originalPlaceholder;
            messageInput.disabled = false;
        }
    };
    
    input.click();
}

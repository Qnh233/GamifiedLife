/**
 * 修改 appendMessage 函数以支持 Markdown 渲染
 */
function appendMessage(text, type) {
    const box = document.getElementById('chat-box');
    const msg = document.createElement('div');
    msg.className = `chat-message ${type}`;

    // 使用 marked 解析 markdown 文本，并将其插入为 HTML
    // 注意：建议在生产环境中配合 DOMPurify 使用以防止 XSS 攻击
    if (typeof marked !== 'undefined') {
        msg.innerHTML = marked.parse(text);
    } else {
        msg.textContent = text;
    }

    box.appendChild(msg);
    box.scrollTop = box.scrollHeight;
}

/**
 * 同时也需要更新 fetchEvents 函数，因为事件描述也可能包含 Markdown
 */
async function fetchEvents() {
    const res = await fetch(`/api/events/${userId}?limit=10`);
    const data = await res.json();
    const list = document.getElementById('events-list');
    list.innerHTML = '';

    data.events.forEach(event => {
        const item = document.createElement('li');
        item.className = 'list-group-item small';
        // 使用 marked 解析描述内容
        const descriptionHtml = typeof marked !== 'undefined' ? marked.parse(event.description) : event.description;
        item.innerHTML = `${new Date(event.created_at).toLocaleTimeString()} - ${descriptionHtml}`;
        list.appendChild(item);
    });
}

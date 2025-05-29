function getCookie(name) {
    const c = document.cookie.split(';').find(x => x.trim().startsWith(name + '='));
    return c ? c.trim().substring(name.length + 1) : '';
}

function delete_source(filePk) {
    console.log(filePk);
    // Make an AJAX DELETE request to your Django backend
    fetch(`/delete-source/${filePk}`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'), // Ensure CSRF token is included
        }
    })
    .then(response => {
        if (response.ok) {
            alert("File deleted successfully!");
            // Optionally, remove the button from the DOM or refresh the list
        } else {
            alert("Failed to delete file.");
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
  const form         = document.querySelector('form.chat-form');
  const conversation = document.getElementById('conversation');
  const promptInput  = form.querySelector('input[name="prompt"]');
  const sendButton   = form.querySelector('button[type="submit"]');
  const project_id   = form.querySelector('input[name="projectID"]')
  let globalThoughtId = 0;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    sendButton.disabled = true;

    // Capture + clear
    const formData = new FormData(form);
    const userText = promptInput.value;
    promptInput.value = '';

    // Fire off request
    const response = await fetch(form.action, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
      body: formData,
    });

    // 1) Show user message
    const userMsg = document.createElement('div');
    userMsg.classList.add('d-flex','align-items-start','mb-3');
    userMsg.innerHTML = `
      <i class="bi bi-person-fill"></i>
      <div class="message ms-3 bg-body-tertiary">${userText}</div>`;
    conversation.appendChild(userMsg);

    // 2) Prepare bot container + one-time accordion
    globalThoughtId += 1;
    const id = globalThoughtId;

    let botMsg, thoughtEl, answerEl, accordionBtn;
    let botMsgAppended = false;
    let thinkFirst = false;

    // 3) Stream into buffers
    let seenStart     = false;
    let seenEnd       = false;
    let thoughtBuffer = '';
    let answerBuffer  = '';
    const reader  = response.body.getReader();
    const decoder = new TextDecoder();
    let done      = false;

    while (!done) {
      const { value, done: streamDone } = await reader.read();
      done = streamDone;
      const chunkText = decoder.decode(value);

      chunkText.split(/\n\n/).forEach(event => {
        if (!event.startsWith('data:')) return;
        const { chunk: text } = JSON.parse(event.replace(/^data: /, ''));

        let remaining = text;

        if (!seenStart) {
          const idx = remaining.indexOf('<think>');
          if (idx !== -1) {
            seenStart = true;
            thinkFirst = idx === 0;
            answerBuffer += remaining.slice(0, idx);
            remaining = remaining.slice(idx + '<think>'.length);
          } else {
            answerBuffer += remaining;
            remaining = '';
          }
        }

        if (!botMsgAppended) {
          // Create botMsg dynamically based on whether <think> was first
          botMsg = document.createElement('div');
          botMsg.classList.add('d-flex','align-items-start','mb-3');

          if (thinkFirst) {
            botMsg.innerHTML = `
              <i class="bi bi-robot"></i>
              <div class="message ms-3 w-100 bg-body-tertiary">
                <div class="accordion mb-2" id="thoughtAccordion${id}">
                  <div class="accordion-item">
                    <h2 class="accordion-header" id="heading${id}">
                      <button class="accordion-button collapsed p-1"
                              type="button"
                              id="accordionToggleBtn${id}"
                              data-bs-toggle="collapse"
                              data-bs-target="#collapse${id}"
                              aria-expanded="false"
                              aria-controls="collapse${id}">
                        Thinking...
                      </button>
                    </h2>
                    <div id="collapse${id}"
                        class="accordion-collapse collapse"
                        aria-labelledby="heading${id}"
                        data-bs-parent="#thoughtAccordion${id}">
                      <div class="accordion-body p-2" id="accordionBody${id}"></div>
                    </div>
                  </div>
                </div>
                <div id="answerContent${id}"></div>
              </div>`;
          } else {
            botMsg.innerHTML = `
              <i class="bi bi-robot"></i>
              <div class="message ms-3 w-100">
                <div id="answerContent${id}"></div>
              </div>`;
          }

          conversation.appendChild(botMsg);
          botMsgAppended = true;

          // set references
          if (thinkFirst) {
            thoughtEl = document.getElementById(`accordionBody${id}`);
            accordionBtn = document.getElementById(`accordionToggleBtn${id}`);
          }
          answerEl = document.getElementById(`answerContent${id}`);
        }

        if (seenStart && !seenEnd && remaining) {
          const closeIdx = remaining.indexOf('</think>');
          if (closeIdx !== -1) {
            thoughtBuffer += remaining.slice(0, closeIdx);
            seenEnd = true;
            if (accordionBtn) accordionBtn.textContent = 'Show thoughts';
            answerBuffer += remaining.slice(closeIdx + '</think>'.length);
          } else {
            thoughtBuffer += remaining;
          }
        }

        if (seenEnd && remaining.indexOf('</think>') === -1) {
          answerBuffer += remaining;
        }

        // Update UI
        if (thinkFirst && thoughtEl) {
          thoughtEl.innerHTML = marked.parse(thoughtBuffer);
        }
        answerEl.innerHTML = marked.parse(answerBuffer);

        conversation.scrollTop = conversation.scrollHeight;
      });
    }
        // 6) Done: persist to server and reload
        sendButton.disabled = false;
        const saveData = new FormData();
        saveData.append('message', `<think>${thoughtBuffer}</think> ${answerBuffer}`);
        saveData.append('is_user', 'false');
        saveData.append('project_id', project_id.value);

        url = window.location.href
        fetch(`${window.location.href.split("/open-project")[0]}/save-system-message/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: saveData
        })
        .then()
        .catch(console.log(e));
    });
});

window.onload = () => {
    const convo = document.getElementById("conversation");
    convo.scrollTop = convo.scrollHeight;
  };
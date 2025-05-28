const urlInput = document.getElementById('floatingUrls');
const chipsContainer = document.getElementById('chipsContainer');
const form = document.getElementById('fileForm')

let fullUrls = [];

urlInput.addEventListener('keydown', (e) => {
if (e.key === ',' || e.key === 'Enter') {
    e.preventDefault(); // Prevent newline or extra commas

    const inputText = urlInput.value.trim();
    const segments = inputText.split(',').map(seg => seg.trim());

    if (segments.length > 0) {
    const lastSegment = segments[segments.length - 1];

    // Extract domain from URL
    const domain = getDomain(lastSegment);
    const fullUrl = lastSegment;

    // Store full URL for submission
    fullUrls.push(fullUrl);

    // Create chip
    const chip = document.createElement('span');
    chip.className = 'badge rounded-pill text-bg-light me-2 mt-2 text-truncate';
    chip.style.maxWidth = "100px"
    chip.textContent = domain;
    chip.role = "button"
    chip.onclick = () => {
        chipsContainer.removeChild(chip);
        fullUrls.splice(fullUrls.indexOf(fullUrl), 1);
        updateChips();
    };
    chipsContainer.appendChild(chip);

    // Clear input
    urlInput.value = segments.slice(0, -1).join(',');
    }
}
});

function getDomain(url) {
try {
    // If URL has protocol, extract hostname
    if (url.startsWith('http://') || url.startsWith('https://')) {
    const parsed = new URL(url);
    return parsed.hostname;
    } else {
    // If URL doesn't have protocol, split on first slash
    const parts = url.split('/');
    return parts[0];
    }
} catch (e) {
    return url; // Fallback for invalid URLs
}
}

function updateChips() {
chipsContainer.innerHTML = '';
fullUrls.forEach(url => {
    const domain = getDomain(url);
    const chip = document.createElement('span');
    chip.className = 'badge rounded-pill text-bg-light me-2 mt-2 text-truncate';
    chip.style.maxWidth = "100px"
    chip.textContent = domain;
    chip.onclick = () => {
    chipsContainer.removeChild(chip);
    fullUrls.splice(fullUrls.indexOf(url), 1);
    updateChips();
    };
    chipsContainer.appendChild(chip);
});
}

form.addEventListener('submit', (e) => {
    e.preventDefault();

    // Set the "urls" input to the full URLs joined by commas
    const urlsInput = document.getElementById('floatingUrls');
    urlsInput.value = fullUrls.join(',');

    // Submit the form
    form.submit();
    form.reset()
});

function validateFile() {
    const files = document.getElementById("file").files;
    const allowedExtensions = [".pdf", ".docx", ".xlsx", ".pptx", ".md", ".html", ".csv", ".png", ".jpeg", ".tiff", ".bmp", ".webp"];

    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      const fileName = file.name.toLowerCase();
      const isValid = allowedExtensions.some(ext => fileName.endsWith(ext));
      if (!isValid) {
          alert("Invalid file type. Only the following formats are allowed: " + allowedExtensions.join(", ") + ".");
          document.getElementById("file").value = "";
      }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file');
    const label = document.getElementById('fileLabel');
    const origLabel = label.innerHTML;
  
    function updateLabelWithFiles(files) {
      const fileArray = Array.from(files);
      const count = fileArray.length;
      const names = fileArray.map(f => f.name).join(', ');
      label.innerHTML = `
        <strong>${count} file${count > 1 ? 's' : ''}</strong>
        <span class="box__dragndrop">${names}</span>
      `;
    }
  
    // Highlight on dragover
    dropzone.addEventListener('dragover', e => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
  
    // Remove highlight on dragleave
    // biome-ignore lint/complexity/noForEach: <explanation>
    ['dragleave', 'dragend'].forEach(evt =>
      dropzone.addEventListener(evt, () => dropzone.classList.remove('dragover'))
    );
  
    // Handle drop
    dropzone.addEventListener('drop', e => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        updateLabelWithFiles(e.dataTransfer.files);
      }
    });
  
    // Handle manual file selection
    fileInput.addEventListener('change', () => {
      if (fileInput.files.length) {
        updateLabelWithFiles(fileInput.files);
      } else {
        label.innerHTML = origLabel;
      }
    });
  });

  window.onload = () => {
    const convo = document.getElementById("conversation");
    convo.scrollTop = convo.scrollHeight;
  };
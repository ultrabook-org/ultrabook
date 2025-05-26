function validateFile() {
    const files = document.getElementById("file").files;
    const allowedExtensions = [".pdf", ".docx", ".xlsx", ".pptx", ".md", ".html", ".csv", ".png", ".jpeg", ".tiff", ".bmp", ".webp"];

    // Check if the file extension is allowed
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      const fileName = file.name.toLowerCase();
      const isValid = allowedExtensions.some(ext => fileName.endsWith(ext));
      if (!isValid) {
          alert("Invalid file type. Only the following formats are allowed: " + allowedExtensions.join(", ") + ".");
          document.getElementById("file").value = ""; // Clear the file input
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
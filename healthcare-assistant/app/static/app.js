document.addEventListener('DOMContentLoaded', () => {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const dropzonePrompt = document.getElementById('dropzonePrompt');
  const filePreviewWrapper = document.getElementById('filePreviewWrapper');
  const previewMedia = document.getElementById('previewMedia');
  const fileName = document.getElementById('fileName');
  const fileSize = document.getElementById('fileSize');
  const removeFileBtn = document.getElementById('removeFileBtn');
  const extractBtn = document.getElementById('extractBtn');
  const extractBtnText = document.getElementById('extractBtnText');

  const extractedCard = document.getElementById('extractedCard');
  const extractedMeta = document.getElementById('extractedMeta');
  const parsedMedicalContainer = document.getElementById('parsedMedicalContainer');
  const jsonCodeOutput = document.getElementById('jsonCodeOutput');
  const textLinesOutput = document.getElementById('textLinesOutput');
  const copyJsonBtn = document.getElementById('copyJsonBtn');

  const simplifyBtn = document.getElementById('simplifyBtn');
  const simplifyBtnText = document.getElementById('simplifyBtnText');
  const copySummaryBtn = document.getElementById('copySummaryBtn');

  const simplifiedCard = document.getElementById('simplifiedCard');
  const simplifiedEmptyState = document.getElementById('simplifiedEmptyState');
  const simplifiedContent = document.getElementById('simplifiedContent');
  const simplifiedSummaryText = document.getElementById('simplifiedSummaryText');
  const toast = document.getElementById('toast');

  const languageSelect = document.getElementById('languageSelect');
  const listenVoiceBtn = document.getElementById('listenVoiceBtn');
  const voiceBtnText = document.getElementById('voiceBtnText');

  let selectedFile = null;
  let currentExtractedData = null;
  let currentSimplifiedData = null;
  let currentAudio = null;

  // Drag & Drop handlers
  dropzone.addEventListener('click', (e) => {
    if (e.target !== removeFileBtn && !removeFileBtn.contains(e.target)) {
      fileInput.click();
    }
  });

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  });

  function handleFileSelected(file) {
    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = (file.size / (1024 * 1024)).toFixed(2) + ' MB';

    dropzonePrompt.classList.add('hidden');
    filePreviewWrapper.classList.remove('hidden');

    previewMedia.innerHTML = '';
    if (file.type.startsWith('image/')) {
      const img = document.createElement('img');
      img.src = URL.createObjectURL(file);
      previewMedia.appendChild(img);
    } else {
      previewMedia.innerHTML = `
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
      `;
    }

    extractBtn.disabled = false;
  }

  removeFileBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    resetUploadState();
  });

  function resetUploadState() {
    selectedFile = null;
    fileInput.value = '';
    dropzonePrompt.classList.remove('hidden');
    filePreviewWrapper.classList.add('hidden');
    previewMedia.innerHTML = '';
    extractBtn.disabled = true;

    simplifiedEmptyState.classList.remove('hidden');
    simplifiedContent.classList.add('hidden');
    copySummaryBtn.disabled = true;

    if (listenVoiceBtn) {
      listenVoiceBtn.disabled = true;
      listenVoiceBtn.style.opacity = '0.5';
    }
  }

  // Extract OCR Data Action
  extractBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    extractBtn.disabled = true;
    extractBtnText.textContent = 'Extracting medical data...';

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch('/extract-text', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Extraction failed');
      }

      const data = await response.json();
      renderExtractedOutput(data);

      simplifiedEmptyState.classList.remove('hidden');
      simplifiedContent.classList.add('hidden');

      showToast('Medical data extracted successfully!');
    } catch (err) {
      showToast('Extraction notice: ' + err.message);
    } finally {
      extractBtn.disabled = false;
      extractBtnText.textContent = 'Extract Medical Data';
    }
  });

  function renderExtractedOutput(data) {
    currentExtractedData = data;
    extractedCard.classList.remove('hidden');

    const medData = data.medical_data || {};
    const rxCount = (medData.prescriptions || []).length;
    const labCount = (medData.diagnostic_lab_results || []).length;
    const vitalsCount = (medData.vital_signs || []).length;

    extractedMeta.textContent = `${data.document_type || 'Medical Document'} (${rxCount} prescriptions, ${vitalsCount} vitals, ${labCount} lab tests)`;
    jsonCodeOutput.textContent = JSON.stringify(data, null, 2);

    parsedMedicalContainer.innerHTML = '';

    if (medData.prescriptions && medData.prescriptions.length > 0) {
      const rxBlock = document.createElement('div');
      rxBlock.className = 'med-block-section';
      rxBlock.innerHTML = `<span class="med-block-title">💊 Prescribed Medicines & Dosages</span>`;

      medData.prescriptions.forEach(p => {
        const card = document.createElement('div');
        card.className = 'prescription-card';
        card.innerHTML = `
          <div class="med-header">
            <span class="med-title">${escapeHtml(p.medicine_name)}</span>
            <span class="med-dosage-badge">${escapeHtml(p.dosage || p.dosage_strength)}</span>
          </div>
          <div class="med-details-grid">
            <div class="med-detail-item"><strong>Frequency:</strong> ${escapeHtml(p.frequency)}</div>
            <div class="med-detail-item"><strong>Timing:</strong> ${escapeHtml(p.timing)}</div>
          </div>
        `;
        rxBlock.appendChild(card);
      });
      parsedMedicalContainer.appendChild(rxBlock);
    }

    textLinesOutput.innerHTML = '';
    const lines = data.medical_lines || [];
    if (lines.length > 0) {
      lines.forEach(line => {
        const lineEl = document.createElement('div');
        lineEl.className = 'text-line-item';
        lineEl.textContent = line;
        textLinesOutput.appendChild(lineEl);
      });
    } else {
      textLinesOutput.innerHTML = '<div class="text-line-item">No clinical text detected.</div>';
    }

    extractedCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // Tabs switching
  document.querySelectorAll('.tab-btn').forEach(tabBtn => {
    tabBtn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));

      tabBtn.classList.add('active');
      const targetId = tabBtn.dataset.tab;
      document.getElementById(targetId).classList.remove('hidden');
    });
  });

  // Copy JSON
  copyJsonBtn.addEventListener('click', () => {
    if (!currentExtractedData) return;
    navigator.clipboard.writeText(JSON.stringify(currentExtractedData, null, 2))
      .then(() => showToast('Medical JSON copied to clipboard!'))
      .catch(() => showToast('Failed to copy.'));
  });

  // Simplify Action Button
  simplifyBtn.addEventListener('click', async () => {
    if (!currentExtractedData) {
      showToast('No extracted medical data available to simplify.');
      return;
    }

    const selectedLanguage = languageSelect ? languageSelect.value : 'en';

    simplifyBtn.disabled = true;
    simplifyBtnText.textContent = selectedLanguage === 'en' ? 'Simplifying Info...' : 'Simplifying & Translating...';

    try {
      const response = await fetch('/simplify-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: currentExtractedData.extracted_text || '',
          medical_data: currentExtractedData.medical_data || {},
          target_language: selectedLanguage
        })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Simplification failed');
      }

      const data = await response.json();
      renderSimplifiedOutput(data);

      const langName = languageSelect ? languageSelect.options[languageSelect.selectedIndex].text : 'Selected Language';
      showToast(`Simplified instructions ready in ${langName}!`);
    } catch (err) {
      showToast('Simplification error: ' + err.message);
    } finally {
      simplifyBtn.disabled = false;
      simplifyBtnText.textContent = 'Simplify Extracted Info';
    }
  });

  function renderSimplifiedOutput(data) {
    currentSimplifiedData = data;
    simplifiedEmptyState.classList.add('hidden');
    simplifiedContent.classList.remove('hidden');
    copySummaryBtn.disabled = false;

    // Enable Voice Guidance Button
    if (listenVoiceBtn) {
      listenVoiceBtn.disabled = false;
      listenVoiceBtn.style.opacity = '1';
    }

    let lines = data.simplified_lines || [];
    if (lines.length === 0 && data.simplified_text) {
      lines = data.simplified_text.split('\n').filter(l => l.trim().length > 0);
    }

    if (lines.length === 0) {
      simplifiedSummaryText.innerHTML = '<div class="text-line-item">No simplified summary available.</div>';
      return;
    }

    let formattedHtml = '';
    lines.forEach(line => {
      let trimmed = line.trim();
      if (trimmed.length > 0) {
        formattedHtml += `
          <div style="
            background: rgba(15, 23, 42, 0.6);
            border-left: 3px solid #38bdf8;
            border-radius: 6px;
            padding: 0.75rem 1rem;
            margin-bottom: 0.65rem;
            color: #f3f4f6;
            font-size: 0.92rem;
            line-height: 1.6;
            word-break: break-word;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
          ">
            ${escapeHtml(trimmed)}
          </div>
        `;
      }
    });

    simplifiedSummaryText.innerHTML = formattedHtml;
    simplifiedCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // Voice Guidance Trigger Listener
  if (listenVoiceBtn) {
    listenVoiceBtn.addEventListener('click', async () => {
      if (!currentSimplifiedData) return;

      const textToSpeak = currentSimplifiedData.simplified_text || '';
      const selectedLanguage = languageSelect ? languageSelect.value : 'en';

      if (currentAudio) {
        currentAudio.pause();
        currentAudio = null;
        voiceBtnText.textContent = 'Listen Voice';
        return;
      }

      voiceBtnText.textContent = 'Playing...';

      try {
        const response = await fetch('/text-to-speech', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: textToSpeak,
            target_language: selectedLanguage
          })
        });

        const data = await response.json();

        if (data.audio_base64) {
          currentAudio = new Audio("data:audio/wav;base64," + data.audio_base64);
          currentAudio.play();
          currentAudio.onended = () => {
            currentAudio = null;
            voiceBtnText.textContent = 'Listen Voice';
          };
        } else {
          playWebSpeechFallback(textToSpeak, selectedLanguage);
        }
      } catch (err) {
        playWebSpeechFallback(textToSpeak, selectedLanguage);
      }
    });
  }

  function playWebSpeechFallback(text, langCode) {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);

      const langMap = {
        'ta': 'ta-IN', 'hi': 'hi-IN', 'te': 'te-IN', 'kn': 'kn-IN',
        'ml': 'ml-IN', 'mr': 'mr-IN', 'bn': 'bn-IN', 'gu': 'gu-IN',
        'or': 'or-IN', 'en': 'en-IN'
      };

      utterance.lang = langMap[langCode] || 'en-IN';
      utterance.rate = 0.9;

      utterance.onend = () => {
        voiceBtnText.textContent = 'Listen Voice';
        currentAudio = null;
      };

      window.speechSynthesis.speak(utterance);
    } else {
      showToast('Speech synthesis not supported on this browser.');
      voiceBtnText.textContent = 'Listen Voice';
    }
  }

  copySummaryBtn.addEventListener('click', () => {
    if (!currentSimplifiedData) return;
    const textToCopy = currentSimplifiedData.simplified_text || '';
    navigator.clipboard.writeText(textToCopy)
      .then(() => showToast('Simplified instructions copied!'))
      .catch(() => showToast('Failed to copy.'));
  });

  function showToast(message) {
    toast.textContent = message;
    toast.classList.remove('hidden');
    setTimeout(() => {
      toast.classList.add('hidden');
    }, 3500);
  }

  function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
});
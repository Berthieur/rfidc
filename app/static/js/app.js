console.log("RFID Door Platform loaded.");

document.addEventListener("DOMContentLoaded", function () {
    // =========================
    // AUTOCOMPLETE AJAX
    // =========================
    const autocompleteInputs = document.querySelectorAll(".autocomplete-input");

    autocompleteInputs.forEach((input) => {
        const url = input.dataset.autocompleteUrl;
        const hiddenTargetId = input.dataset.hiddenTarget;
        const hiddenInput = document.getElementById(hiddenTargetId);
        const resultsBox = document.getElementById(`${input.id}_results`);

        if (!url || !hiddenInput || !resultsBox) {
            return;
        }

        let debounceTimer = null;

        function clearResults() {
            resultsBox.innerHTML = "";
            resultsBox.style.display = "none";
        }

        function showResults(items) {
            if (!items.length) {
                clearResults();
                return;
            }

            resultsBox.innerHTML = "";

            items.forEach((item) => {
                const resultItem = document.createElement("button");
                resultItem.type = "button";
                resultItem.className = "autocomplete-result-item";
                resultItem.textContent = item.label;

                resultItem.addEventListener("click", function () {
                    input.value = item.label;
                    hiddenInput.value = item.id;
                    clearResults();
                });

                resultsBox.appendChild(resultItem);
            });

            resultsBox.style.display = "block";
        }

        input.addEventListener("input", function () {
            const query = input.value.trim();

            if (hiddenInput.value && query === "") {
                hiddenInput.value = "";
            }

            if (query.length < 2) {
                clearResults();
                return;
            }

            clearTimeout(debounceTimer);

            debounceTimer = setTimeout(async function () {
                try {
                    const response = await fetch(`${url}?q=${encodeURIComponent(query)}`);
                    if (!response.ok) {
                        clearResults();
                        return;
                    }

                    const data = await response.json();
                    showResults(data);
                } catch (error) {
                    clearResults();
                }
            }, 250);
        });

        input.addEventListener("blur", function () {
            setTimeout(() => clearResults(), 150);
        });

        input.addEventListener("focus", function () {
            const query = input.value.trim();
            if (query.length >= 2) {
                input.dispatchEvent(new Event("input"));
            }
        });
    });

    // =========================
    // UID CAPTURE RFID CARD CREATE
    // =========================
    const uidInput = document.getElementById("uid");
    const uidHiddenInput = document.getElementById("uid_hidden");
    const startBtn = document.getElementById("startUidCaptureBtn");
    const statusBox = document.getElementById("uidCaptureStatus");

    if (!uidInput || !uidHiddenInput || !startBtn || !statusBox) {
        return;
    }

    let captureId = null;
    let pollTimer = null;
    let animationTimer = null;
    let dots = 0;

    function stopPolling() {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    }

    function stopDotsAnimation() {
        if (animationTimer) {
            clearInterval(animationTimer);
            animationTimer = null;
        }
    }

    function startDotsAnimation(baseText) {
        stopDotsAnimation();
        dots = 0;

        animationTimer = setInterval(() => {
            dots = (dots + 1) % 4;
            statusBox.textContent = `${baseText}${".".repeat(dots)}`;
        }, 450);
    }

    function setIdleState() {
        startBtn.disabled = false;
        startBtn.textContent = "Lire depuis le capteur";
        stopDotsAnimation();
    }

    function setWaitingState() {
        startBtn.disabled = true;
        startBtn.textContent = "Lecture en cours";
        startDotsAnimation("Attente d’un badge RFID");
    }

    function setSuccessState() {
        startBtn.disabled = true;
        startBtn.textContent = "UID capturé";
        stopDotsAnimation();

        uidInput.disabled = true;
        uidInput.classList.add("uid-captured-success");
        uidInput.style.userSelect = "none";
        uidInput.style.pointerEvents = "none";
    }

    function resetUidFieldVisualState() {
        uidInput.disabled = false;
        uidInput.classList.remove("uid-captured-success");
        uidInput.style.userSelect = "";
        uidInput.style.pointerEvents = "";
    }

    async function pollCaptureStatus() {
        if (!captureId) {
            return;
        }

        try {
            const response = await fetch(`/rfid-cards/uid-capture/status/${captureId}`);

            if (!response.ok) {
                stopPolling();
                setIdleState();
                resetUidFieldVisualState();
                statusBox.textContent = "Échec de lecture UID.";
                return;
            }

            const data = await response.json();

            if (data.status === "success") {
                const capturedUid = data.uid || "";
                uidInput.value = capturedUid;
                uidHiddenInput.value = capturedUid;
                setSuccessState();
                statusBox.textContent = "UID capturé avec succès.";
                stopPolling();
                return;
            }

            if (data.status === "expired") {
                stopPolling();
                captureId = null;
                setIdleState();
                resetUidFieldVisualState();
                statusBox.textContent = "Échec : aucun badge détecté dans les 15 secondes.";
                return;
            }

            if (data.status === "not_found") {
                stopPolling();
                captureId = null;
                setIdleState();
                resetUidFieldVisualState();
                statusBox.textContent = "Aucune session de lecture active.";
            }
        } catch (error) {
            stopPolling();
            captureId = null;
            setIdleState();
            resetUidFieldVisualState();
            statusBox.textContent = "Erreur réseau pendant la lecture UID.";
        }
    }

    startBtn.addEventListener("click", async function () {
        if (startBtn.disabled) {
            return;
        }

        stopPolling();
        resetUidFieldVisualState();

        uidInput.value = "";
        uidHiddenInput.value = "";

        setWaitingState();

        try {
            const response = await fetch("/rfid-cards/uid-capture/start", {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            });

            if (!response.ok) {
                setIdleState();
                statusBox.textContent = "Impossible de démarrer la lecture depuis le capteur.";
                return;
            }

            const data = await response.json();
            captureId = data.capture_id;
            pollTimer = setInterval(pollCaptureStatus, 1000);
        } catch (error) {
            setIdleState();
            statusBox.textContent = "Impossible de démarrer la lecture depuis le capteur.";
        }
    });
});
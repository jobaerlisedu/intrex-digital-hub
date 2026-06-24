document.addEventListener("DOMContentLoaded", function () {

  /* ── Contact / Inquiry Form ─────────────────────────────────── */
  const contactForm = document.getElementById("contactForm");
  const successMessage = document.getElementById("successMessage");
  const errorMessage = document.getElementById("errorMessage");

  if (contactForm) {
    contactForm.addEventListener("submit", function (event) {
      event.preventDefault();

      const submitBtn = contactForm.querySelector('button[type="submit"]');
      const originalBtnText = submitBtn.textContent;
      submitBtn.disabled = true;
      submitBtn.textContent = "Sending...";

      successMessage.classList.add("d-none");
      errorMessage.classList.add("d-none");

      const name = (document.getElementById("name")?.value || "").trim();
      const email = (document.getElementById("email")?.value || "").trim();
      const phone = (document.getElementById("phone")?.value || "").trim();
      const subject = (document.getElementById("subject")?.value || "").trim();
      const message = (document.getElementById("message")?.value || "").trim();

      // Resolve module path depending on root or sub-directory location
      let importPath = "/assets/js/training.js";
      if (window.location.hostname === "" || window.location.protocol === "file:") {
        const depth = window.location.pathname.split("/services/").length > 1 ? "../" : "./";
        importPath = depth + "assets/js/training.js";
      }

      import(importPath)
        .then(async (module) => {
          try {
            let source = "home-page";
            if (window.location.pathname.includes("service-")) {
              source = window.location.pathname.substring(window.location.pathname.lastIndexOf("/") + 1).replace(".html", "");
            }

            // Save inquiry in Firestore
            const inquiryKey = await module.addOnlineInquiry({
              name,
              email,
              phone,
              subject,
              message,
              source
            });

            submitBtn.disabled = false;
            submitBtn.textContent = originalBtnText;

            successMessage.innerHTML = `
              <div class="w-100">
                <div class="d-flex align-items-center gap-2 mb-2 text-success">
                  <i class="bi bi-check-circle-fill fs-5"></i>
                  <span class="fw-bold">Inquiry Sent!</span>
                </div>
                <p class="small text-muted mb-2">Your inquiry reference key:</p>
                <div class="d-flex align-items-center gap-2 bg-body-secondary p-2 rounded-3 border mb-2">
                  <code class="fw-bold font-monospace flex-grow-1" id="generatedInqKeyVal" style="color: var(--bs-heading-color);">${inquiryKey}</code>
                  <button class="btn btn-sm btn-primary py-1 px-2 d-flex align-items-center gap-1" id="copyInqKeyBtn" type="button">
                    <i class="bi bi-clipboard"></i> <span>Copy</span>
                  </button>
                </div>
                <p class="small text-muted mb-0"><i class="bi bi-info-circle me-1"></i>We will respond shortly.</p>
              </div>
            `;
            successMessage.className = "mt-3 alert alert-success d-flex align-items-start border border-success p-3 rounded-4 shadow-sm";
            successMessage.classList.remove("d-none");

            // Bind copy logic
            const copyBtn = document.getElementById("copyInqKeyBtn");
            if (copyBtn) {
              copyBtn.onclick = () => {
                navigator.clipboard.writeText(inquiryKey);
                copyBtn.innerHTML = '<i class="bi bi-check-lg"></i> <span>Copied</span>';
                copyBtn.className = "btn btn-sm btn-success py-1 px-2 d-flex align-items-center gap-1";
                setTimeout(() => {
                  copyBtn.innerHTML = '<i class="bi bi-clipboard"></i> <span>Copy</span>';
                  copyBtn.className = "btn btn-sm btn-primary py-1 px-2 d-flex align-items-center gap-1";
                }, 1500);
              };
            }

            contactForm.reset();
          } catch (err) {
            console.error("Firestore inquiry write error:", err);
            submitBtn.disabled = false;
            submitBtn.textContent = originalBtnText;
            errorMessage.textContent = "Failed to submit inquiry: " + (err.message || "Please try again.");
            errorMessage.classList.remove("d-none");
          }
        })
        .catch((err) => {
          console.error("Failed to dynamically import training.js module:", err);
          submitBtn.disabled = false;
          submitBtn.textContent = originalBtnText;
          errorMessage.textContent = "Unable to connect. Please check your network and try again.";
          errorMessage.classList.remove("d-none");
        });
    });
  }

  /* ── Newsletter Form ────────────────────────────────────────── */
  const newsletterForm = document.getElementById("newsletterForm");

  if (newsletterForm) {
    newsletterForm.addEventListener("submit", function (event) {
      event.preventDefault();

      const submitBtn = newsletterForm.querySelector('button[type="submit"]');
      const feedback = document.getElementById("newsletterFeedback");
      const originalBtnText = submitBtn.textContent;
      submitBtn.disabled = true;
      submitBtn.textContent = "Subscribing...";
      if (feedback) {
        feedback.textContent = "";
        feedback.className = "small mt-2";
      }

      const emailInput = newsletterForm.querySelector('input[type="email"]');
      const email = (emailInput?.value || "").trim();

      if (!email) {
        if (feedback) {
          feedback.textContent = "Email address is required.";
          feedback.classList.add("text-danger");
        }
        submitBtn.disabled = false;
        submitBtn.textContent = originalBtnText;
        return;
      }

      // Resolve module path depending on root or sub-directory location
      let importPath = "/assets/js/training.js";
      if (window.location.hostname === "" || window.location.protocol === "file:") {
        const depth = window.location.pathname.split("/services/").length > 1 ? "../" : "./";
        importPath = depth + "assets/js/training.js";
      }

      import(importPath)
        .then(async (module) => {
          try {
            await module.addNewsletterSubscription(email);
            submitBtn.disabled = false;
            submitBtn.textContent = originalBtnText;
            newsletterForm.reset();
            if (feedback) {
              feedback.textContent = "✓ You're subscribed! Thank you.";
              feedback.className = "small mt-2 text-success fw-semibold";
            }
          } catch (err) {
            console.error("Newsletter registration error:", err);
            submitBtn.disabled = false;
            submitBtn.textContent = originalBtnText;
            if (feedback) {
              feedback.textContent = "Subscription failed: " + (err.message || "Please try again.");
              feedback.className = "small mt-2 text-danger";
            }
          }
        })
        .catch((err) => {
          console.error("Failed to dynamically import training.js module:", err);
          submitBtn.disabled = false;
          submitBtn.textContent = originalBtnText;
          if (feedback) {
            feedback.textContent = "Unable to connect. Please try again.";
            feedback.className = "small mt-2 text-danger";
          }
        });
    });
  }


});

document.addEventListener("DOMContentLoaded", function () {

  // ======= Section-based nav active state =======
  const sections = document.querySelectorAll(".section");
  const navLinks = document.querySelectorAll(".fbs__net-navbar .scroll-link");

  function removeActiveClasses() {
    navLinks.forEach((link) => link.classList.remove("active"));
  }

  function addActiveClass(currentSectionId) {
    const activeLink = document.querySelector(
      `.fbs__net-navbar .scroll-link[href$="#${currentSectionId}"]`
    );
    if (activeLink) {
      activeLink.classList.add("active");
    }
  }

  function getCurrentSection() {
    let currentSection = null;
    let minDistance = Infinity;
    sections.forEach((section) => {
      const rect = section.getBoundingClientRect();
      const distance = Math.abs(rect.top - window.innerHeight / 4);
      if (distance < minDistance && rect.top < window.innerHeight) {
        minDistance = distance;
        currentSection = section.getAttribute("id");
      }
    });
    return currentSection;
  }

  function updateActiveLink() {
    const currentSectionId = getCurrentSection();
    if (currentSectionId) {
      removeActiveClasses();
      addActiveClass(currentSectionId);
    }
  }

  window.addEventListener("scroll", updateActiveLink);

  // ======= Isotope / Portfolio (only if library is loaded) =======
  const portfolioGrid = document.querySelector('#portfolio-grid');
  if (portfolioGrid && typeof Isotope !== 'undefined' && typeof imagesLoaded !== 'undefined') {
    const iso = new Isotope("#portfolio-grid", {
      itemSelector: ".portfolio-item",
      layoutMode: "masonry",
    });

    iso.on("layoutComplete", updateActiveLink);

    imagesLoaded("#portfolio-grid", function () {
      iso.layout();
      updateActiveLink();
    });

    const filterButtons = document.querySelectorAll(".filter-button");
    filterButtons.forEach(function (button) {
      button.addEventListener("click", function (e) {
        e.preventDefault();
        const filterValue = button.getAttribute("data-filter");
        iso.arrange({ filter: filterValue });
        filterButtons.forEach(function (btn) {
          btn.classList.remove("active");
        });
        button.classList.add("active");
        updateActiveLink();
      });
    });

    updateActiveLink();
  }

  // ======= Navbar scroll behavior =======
  const navbar = document.querySelector(".fbs__net-navbar");
  function navbarScrollInit() {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    if (scrollTop > 0) {
      navbar.classList.add("active");
    } else {
      navbar.classList.remove("active");
    }
  }
  window.addEventListener("scroll", navbarScrollInit);

  // ======= Navbar dropdown: prevent click on href="#" =======
  document.querySelectorAll('.dropdown-toggle[href="#"]').forEach(function (el) {
    el.addEventListener("click", function (event) {
      event.stopPropagation();
    });
  });

  // ======= Swiper =======
  if (typeof Swiper !== 'undefined') {
    new Swiper(".testimonialSwiper", {
      slidesPerView: 1,
      speed: 700,
      spaceBetween: 30,
      loop: true,
      pagination: {
        el: ".swiper-pagination",
        clickable: true,
      },
      breakpoints: {
        640: { slidesPerView: 1.5, spaceBetween: 20 },
        768: { slidesPerView: 2.5, spaceBetween: 30 },
        1024: { slidesPerView: 2.5, spaceBetween: 30 },
      },
      navigation: {
        nextEl: ".custom-button-next",
        prevEl: ".custom-button-prev",
      },
    });

    const progressCircle = document.querySelector(".autoplay-progress svg");
    const progressContent = document.querySelector(".autoplay-progress span");
    if (progressCircle && progressContent) {
      new Swiper(".sliderSwiper", {
        slidesPerView: 1,
        speed: 700,
        spaceBetween: 0,
        loop: true,
        centeredSlides: true,
        autoplay: {
          delay: 7000,
          disableOnInteraction: false,
        },
        pagination: {
          el: ".swiper-pagination",
          clickable: true,
        },
        navigation: {
          nextEl: ".custom-button-next",
          prevEl: ".custom-button-prev",
        },
        on: {
          autoplayTimeLeft(s, time, progress) {
            progressCircle.style.setProperty("--progress", 1 - progress);
            progressContent.textContent = `${Math.ceil(time / 1000)}s`;
          },
        },
      });
    }
  }

  // ======= Glightbox =======
  if (typeof GLightbox !== 'undefined') {
    GLightbox({
      touchNavigation: true,
      loop: true,
      autoplayVideos: true,
    });
  }

  // ======= BS OffCanvas =======
  const offcanvasElement = document.getElementById("fbs__net-navbars");
  if (offcanvasElement) {
    offcanvasElement.addEventListener("show.bs.offcanvas", function () {
      document.body.classList.add("offcanvas-active");
    });
    offcanvasElement.addEventListener("hidden.bs.offcanvas", function () {
      document.body.classList.remove("offcanvas-active");
    });
  }

  // ======= Back To Top =======
  const backToTopButton = document.getElementById("back-to-top");
  if (backToTopButton) {
    window.addEventListener("scroll", () => {
      if (window.scrollY > 170) {
        backToTopButton.classList.add("show");
      } else {
        backToTopButton.classList.remove("show");
      }
    });
    backToTopButton.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  // ======= Inline SVG =======
  const imgElements = document.querySelectorAll(".js-img-to-inline-svg");
  imgElements.forEach((imgElement) => {
    const imgURL = imgElement.getAttribute("src");
    fetch(imgURL)
      .then((response) => response.text())
      .then((svgText) => {
        const parser = new DOMParser();
        const svgDocument = parser.parseFromString(svgText, "image/svg+xml");
        const svgElement = svgDocument.documentElement;
        Array.from(imgElement.attributes).forEach((attr) => {
          if (attr.name !== "class") {
            svgElement.setAttribute(attr.name, attr.value);
          } else {
            const classes = attr.value
              .split(" ")
              .filter((className) => className !== "js-img-to-inline-svg");
            if (classes.length > 0) {
              svgElement.setAttribute("class", classes.join(" "));
            }
          }
        });
        imgElement.replaceWith(svgElement);
      })
      .catch((error) => console.error("Error fetching SVG:", error));
  });

  // ======= AOS =======
  if (typeof AOS !== 'undefined') {
    AOS.init({
      duration: 800,
      easing: 'slide',
      once: true,
    });
  }

  // ======= PureCounter =======
  if (typeof PureCounter !== 'undefined') {
    new PureCounter({ selector: ".purecounter" });
  }

  // ======= Navbar dropdown hover/click behavior =======
  const addHoverEvents = (dropdown) => {
    const dropdownToggle = dropdown.querySelector('.dropdown-toggle');
    const preventClick = (event) => event.preventDefault();
    const showDropdown = () => {
      dropdown.classList.add('show');
      dropdownToggle.setAttribute('aria-expanded', 'true');
      const dropdownMenu = dropdown.querySelector('.dropdown-menu');
      if (dropdownMenu) dropdownMenu.classList.add('show');
    };
    const hideDropdown = () => {
      dropdown.classList.remove('show');
      dropdownToggle.setAttribute('aria-expanded', 'false');
      const dropdownMenu = dropdown.querySelector('.dropdown-menu');
      if (dropdownMenu) dropdownMenu.classList.remove('show');
    };

    dropdownToggle.addEventListener('click', preventClick);
    dropdown.addEventListener('mouseover', showDropdown);
    dropdown.addEventListener('mouseleave', hideDropdown);

    // Keyboard accessibility: Enter/Space to toggle
    dropdownToggle.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        const isOpen = dropdown.classList.contains('show');
        if (isOpen) {
          hideDropdown();
        } else {
          showDropdown();
        }
      }
    });

    // Close on Escape
    dropdown.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        hideDropdown();
        dropdownToggle.focus();
      }
    });

    dropdown.__events = { preventClick, showDropdown, hideDropdown };
  };

  const removeHoverEvents = (dropdown) => {
    const dropdownToggle = dropdown.querySelector('.dropdown-toggle');
    const { preventClick, showDropdown, hideDropdown } = dropdown.__events || {};
    if (preventClick) {
      dropdownToggle.removeEventListener('click', preventClick);
      dropdown.removeEventListener('mouseover', showDropdown);
      dropdown.removeEventListener('mouseleave', hideDropdown);
      delete dropdown.__events;
    }
  };

  const handleNavbarEvents = () => {
    const dropdowns = document.querySelectorAll('.navbar .dropdown, .navbar .dropstart, .navbar .dropend');
    if (window.innerWidth >= 992) {
      dropdowns.forEach(addHoverEvents);
    } else {
      dropdowns.forEach(removeHoverEvents);
    }
  };

  const handleResize = () => {
    document.querySelectorAll('.navbar .dropdown, .navbar .dropstart, .navbar .dropend')
      .forEach(removeHoverEvents);
    handleNavbarEvents();
  };

  window.addEventListener('resize', handleResize);
  handleNavbarEvents();

  // ======= Coming Soon Countdown =======
  (function countdownInit() {
    const currentYear = new Date().getFullYear();
    const nextYear = currentYear + 1;
    const launchDate = new Date(`December 31, ${nextYear} 23:59:59`).getTime();

    const x = setInterval(function () {
      const now = new Date().getTime();
      const distance = launchDate - now;

      const days = Math.floor(distance / (1000 * 60 * 60 * 24));
      const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((distance % (1000 * 60)) / 1000);

      const daysEl = document.getElementById("days");
      const hoursEl = document.getElementById("hours");
      const minutesEl = document.getElementById("minutes");
      const secondsEl = document.getElementById("seconds");
      if (daysEl) daysEl.innerText = days;
      if (hoursEl) hoursEl.innerText = hours;
      if (minutesEl) minutesEl.innerText = minutes;
      if (secondsEl) secondsEl.innerText = seconds;

      if (distance < 0) {
        clearInterval(x);
        const cd = document.querySelector(".countdown");
        if (cd) cd.innerText = "Launched!";
      }
    }, 1000);
  })();

  // ======= Newsletter Form =======
  const newsletterForm = document.getElementById("newsletterForm");
  const newsletterFeedback = document.getElementById("newsletterFeedback");
  if (newsletterForm) {
    newsletterForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      const emailInput = newsletterForm.querySelector('input[name="email"]');
      const email = emailInput.value.trim();
      if (!email) return;

      const submitBtn = newsletterForm.querySelector('button[type="submit"]');
      const originalText = submitBtn.textContent;
      submitBtn.disabled = true;
      submitBtn.textContent = "Subscribing...";

      try {
        const response = await fetch("/courses/inquire/", {
          method: "POST",
          body: new URLSearchParams({ name: "Newsletter", email, subject: "Newsletter Subscription", message: "Subscribe me to the newsletter" }),
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest",
          },
        });
        const result = response.ok ? await response.json() : null;
        if (result && result.status === "success") {
          newsletterFeedback.textContent = "Thank you for subscribing!";
          newsletterFeedback.className = "small mt-2 text-success";
          emailInput.value = "";
        } else {
          newsletterFeedback.textContent = "Subscription failed. Please try again.";
          newsletterFeedback.className = "small mt-2 text-danger";
        }
      } catch {
        newsletterFeedback.textContent = "An error occurred. Please try again.";
        newsletterFeedback.className = "small mt-2 text-danger";
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
      }
    });
  }

  // ======= Global Contact Form Submit Handler (non-contact pages) =======
  const contactForm = document.getElementById("contactForm");
  if (contactForm && !window.location.pathname.includes("/contact/")) {
    // Only handle contactForm when it's NOT the contact page
    // (training page also has a form with id contactForm, handled by its own inline script)
    const isTrainingPage = window.location.pathname.includes("/courses/");
    if (!isTrainingPage) {
      contactForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const successMessage = document.getElementById("successMessage");
        const errorMessage = document.getElementById("errorMessage");
        const submitBtn = contactForm.querySelector('button[type="submit"]');

        if (successMessage) successMessage.classList.add("d-none");
        if (errorMessage) errorMessage.classList.add("d-none");

        const originalBtnText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Sending...';

        const formData = new FormData(contactForm);
        formData.append("source", window.location.pathname);

        try {
          const response = await fetch("/courses/inquire/", {
            method: "POST",
            body: formData,
            headers: {
              "X-Requested-With": "XMLHttpRequest",
            },
          });

          const result = response.ok ? await response.json() : null;

          if (result && result.status === "success") {
            if (successMessage) {
              successMessage.classList.remove("d-none");
              const refKeyEl = successMessage.querySelector("strong");
              if (refKeyEl && result.key) {
                refKeyEl.textContent = result.key;
              }
            }
            contactForm.reset();
          } else {
            if (errorMessage) errorMessage.classList.remove("d-none");
          }
        } catch {
          if (errorMessage) errorMessage.classList.remove("d-none");
        } finally {
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalBtnText;
        }
      });
    }
  }
});

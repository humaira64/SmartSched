document.addEventListener("DOMContentLoaded", function () {

    // =========================================================
    // COMMON — SIDEBAR
    // =========================================================

    const sidebar = document.querySelector(".sidebar");
    const sidebarToggle = document.querySelector(".sidebar-toggle");

    if (sidebar && sidebarToggle) {

        const savedState =
            localStorage.getItem("sidebarState");

        if (savedState === "collapsed") {
            sidebar.classList.add("active");
        } else {
            sidebar.classList.remove("active");
        }

        sidebarToggle.addEventListener("click", function () {

            sidebar.classList.toggle("active");

            if (sidebar.classList.contains("active")) {

                localStorage.setItem(
                    "sidebarState",
                    "collapsed"
                );

            } else {

                localStorage.setItem(
                    "sidebarState",
                    "expanded"
                );

            }

        });

    }


    // =========================================================
    // COMMON — DELETE CONFIRMATION
    // =========================================================

    const deleteButtons =
        document.querySelectorAll(".delete-confirm");

    deleteButtons.forEach(function (button) {

        button.addEventListener("click", function (event) {

            const message =
                this.dataset.message ||
                "Are you sure you want to delete this record?";

            if (!confirm(message)) {
                event.preventDefault();
            }

        });

    });


    // =========================================================
    // COMMON — FLASH MESSAGE
    // =========================================================

    const alerts =
        document.querySelectorAll(".alert");

    alerts.forEach(function (alert) {

        setTimeout(function () {

            alert.style.transition =
                "opacity 0.4s ease";

            alert.style.opacity = "0";

            setTimeout(function () {

                alert.remove();

            }, 400);

        }, 4000);

    });

});


document.addEventListener("DOMContentLoaded", function () {

    // =====================================================
    // STUDENT - FIND SUBJECTS SEARCH
    // =====================================================

    const searchInput =
        document.getElementById("subjectSearch");

    const searchButton =
        document.getElementById("searchButton");

    const subjectCards =
        document.querySelectorAll(".dynamic-subject");

    const subjectCount =
        document.getElementById("subjectCount");


    if (
        searchInput &&
        searchButton &&
        subjectCount
    ) {

        function filterSubjects() {

            const keyword =
                searchInput.value
                    .toLowerCase()
                    .trim();

            let visibleCount = 0;

            subjectCards.forEach(function (card) {

                const searchText =
                    card.dataset.search.toLowerCase();

                if (searchText.includes(keyword)) {

                    card.style.display = "";
                    visibleCount++;

                } else {

                    card.style.display = "none";

                }

            });

            subjectCount.textContent =
                visibleCount;
        }


        searchButton.addEventListener(
            "click",
            filterSubjects
        );


        searchInput.addEventListener(
            "keyup",
            function (event) {

                if (event.key === "Enter") {
                    filterSubjects();
                }

            }
        );

    }


    // =====================================================
    // STUDENT - PROGRAMME FILTER
    // =====================================================

    const programmeFilter =
        document.getElementById("programmeFilter");


    if (programmeFilter) {

        programmeFilter.addEventListener(
            "change",
            function () {

                const programme =
                    this.value;

                const semesterFilter =
                    document.getElementById(
                        "semesterFilter"
                    );

                const semester =
                    semesterFilter
                        ? semesterFilter.value
                        : "all";


                window.location.href =
                    "/find-subjects?programme=" +
                    encodeURIComponent(programme) +
                    "&semester=" +
                    encodeURIComponent(semester);

            }
        );

    }


    // =====================================================
    // STUDENT - SEMESTER FILTER
    // =====================================================

    const semesterFilter =
        document.getElementById(
            "semesterFilter"
        );


    if (semesterFilter) {

        semesterFilter.addEventListener(
            "change",
            function () {

                const semester =
                    this.value;

                const programmeFilter =
                    document.getElementById(
                        "programmeFilter"
                    );

                const programme =
                    programmeFilter
                        ? programmeFilter.value
                        : "";


                window.location.href =
                    "/find-subjects?programme=" +
                    encodeURIComponent(programme) +
                    "&semester=" +
                    encodeURIComponent(semester);

            }
        );

    }

});

/* =====================================================
   TIMETABLE SETTINGS
   ===================================================== */

const settingsBtn =
    document.getElementById("timetableSettingsBtn");

const settingsPanel =
    document.getElementById("timetableSettingsPanel");

const closeSettings =
    document.getElementById("closeTimetableSettings");


if (settingsBtn && settingsPanel) {

    settingsBtn.addEventListener("click", function () {

        settingsPanel.classList.toggle("show");

    });

}


if (closeSettings && settingsPanel) {

    closeSettings.addEventListener("click", function () {

        settingsPanel.classList.remove("show");

    });

}


/* =====================================================
   SHOW WEEKEND
   ===================================================== */

const weekendToggle =
    document.getElementById("showWeekendToggle");

if (weekendToggle) {

    weekendToggle.addEventListener("change", function () {

        document
            .querySelectorAll(
                '.compact-day-row[data-day="Saturday"], .compact-day-row[data-day="Sunday"]'
            )
            .forEach(function (row) {

                row.style.display =
                    this.checked ? "grid" : "none";

            }, this);

    });

}


/* =====================================================
   WHITE BACKGROUND
   ===================================================== */

const whiteBackgroundToggle =
    document.getElementById("whiteBackgroundToggle");

if (whiteBackgroundToggle) {

    whiteBackgroundToggle.addEventListener(
        "change",
        function () {

            const timetable =
                document.getElementById(
                    "compactTimetable"
                );

            if (!timetable) {
                return;
            }

            timetable.classList.toggle(
                "colored-background",
                !this.checked
            );

        }
    );

}
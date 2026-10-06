document.addEventListener("DOMContentLoaded", function () {

    // =====================================================
    // SIDEBAR
    // =====================================================

    const sidebar = document.getElementById("sidebar");
    const menuBtn = document.getElementById("menu-btn");

    if (sidebar && menuBtn) {

        const savedState =
            localStorage.getItem("sidebarState");

        if (savedState === "collapsed") {
            sidebar.classList.add("active");
        } else {
            sidebar.classList.remove("active");
        }

        menuBtn.addEventListener("click", function () {

            sidebar.classList.toggle("active");

            localStorage.setItem(
                "sidebarState",
                sidebar.classList.contains("active")
                    ? "collapsed"
                    : "expanded"
            );

        });
    }


    // =====================================================
    // FILTERS
    // =====================================================

    const sessionFilter =
        document.getElementById("sessionFilter");

    const programmeFilter =
        document.getElementById("programmeFilter");

    const semesterFilter =
        document.getElementById("semesterFilter");


    function getFilterValues() {

        return {
            session: sessionFilter
                ? sessionFilter.value
                : "",

            programme: programmeFilter
                ? programmeFilter.value
                : "",

            semester: semesterFilter
                ? semesterFilter.value
                : ""
        };

    }


    // =====================================================
    // FIND TIMETABLE
    // =====================================================

    const findButton =
        document.getElementById("findTimetableBtn");

    if (findButton) {

        findButton.addEventListener("click", function () {

            const filters = getFilterValues();

            if (!filters.session) {
                alert("Please select Academic Session.");
                return;
            }

            if (!filters.programme) {
                alert("Please select Programme.");
                return;
            }

            if (!filters.semester) {
                alert("Please select Semester.");
                return;
            }


            window.location.href =
                "/admin/manage-timetable" +
                "?session=" +
                encodeURIComponent(filters.session) +
                "&programme=" +
                encodeURIComponent(filters.programme) +
                "&semester=" +
                encodeURIComponent(filters.semester);

        });

    }


    // =====================================================
    // CREATE NEW TIMETABLE
    // =====================================================

    const createButton =
        document.getElementById("createNewTimetableBtn");

    if (createButton) {

        createButton.addEventListener("click", function () {

            const filters = getFilterValues();

            if (!filters.session) {
                alert("Please select Academic Session.");
                return;
            }

            if (!filters.programme) {
                alert("Please select Programme.");
                return;
            }

            if (!filters.semester) {
                alert("Please select Semester.");
                return;
            }


            window.location.href =
                "/admin/manage-timetable" +
                "?session=" +
                encodeURIComponent(filters.session) +
                "&programme=" +
                encodeURIComponent(filters.programme) +
                "&semester=" +
                encodeURIComponent(filters.semester) +
                "&create=1";

        });

    }


    // =====================================================
    // PERIOD TIME TOOLTIP
    // =====================================================

    const periodHeaders =
        document.querySelectorAll(".period-header-cell");

    periodHeaders.forEach(function (header) {

        const period =
            parseInt(header.dataset.period);

        if (!period) {
            return;
        }

        header.title =
            getPeriodTime(period);

    });


    function formatHour(hour) {

        const suffix =
            hour >= 12 ? "PM" : "AM";

        let h = hour % 12;

        if (h === 0) {
            h = 12;
        }

        return h + ":00 " + suffix;

    }


    function getPeriodTime(period) {

        period = parseInt(period);

        if (!period) {
            return "";
        }

        const startHour =
            7 + period;

        const endHour =
            startHour + 1;

        return (
            formatHour(startHour) +
            " – " +
            formatHour(endHour)
        );

    }


    // =====================================================
// PERIOD HEADER + SLOT CLICK
// =====================================================

// CLICK PERIOD NUMBER (1, 2, 3, 4...)
// This allows admin to add a subject directly
// by clicking the period box.

document
    .querySelectorAll(".period-header-cell")
    .forEach(function (header) {

        header.addEventListener("click", function (event) {

            event.stopPropagation();

            const period =
                this.dataset.period;

            if (!period) {
                return;
            }


            // Find the timetable table for this day
            const table =
                this.closest(".day-timetable");

            if (!table) {
                return;
            }


            // Find the slot with the same period
            const slot =
                table.querySelector(
                    `.timetable-slot[data-period="${period}"]`
                );

            if (!slot) {
                return;
            }


            const day =
                slot.dataset.day;


            // Open Add Subject modal
            openSubjectModal(
                day,
                period
            );

        });

    });


// =====================================================
// SLOT CLICK
// =====================================================

// Empty timetable area is also clickable.

document
    .querySelectorAll(".timetable-slot")
    .forEach(function (slot) {

        slot.addEventListener("click", function (event) {

            // If user clicked an existing subject card,
            // do NOT open Add Subject.
            if (
                event.target.closest(
                    ".scheduled-class"
                )
            ) {
                return;
            }


            openSubjectModal(
                this.dataset.day,
                this.dataset.period
            );

        });

    });


    // =====================================================
    // OPEN SUBJECT MODAL
    // =====================================================

    function openSubjectModal(day, period) {

        const modal =
            document.getElementById("subjectModal");

        if (!modal) {
            return;
        }


        modal.dataset.day = day;
        modal.dataset.period = period;


        const selectedSlot =
            document.getElementById("selectedSlot");

        if (selectedSlot) {

            selectedSlot.textContent =
                day +
                " • Period " +
                period +
                " • " +
                getPeriodTime(period);

        }


        const search =
            document.getElementById("subjectSearch");

        if (search) {
            search.value = "";
        }


        filterSubjects("");


        if (typeof bootstrap !== "undefined") {

            bootstrap.Modal
                .getOrCreateInstance(modal)
                .show();

        } else {

            modal.classList.add("show");
            modal.style.display = "block";

        }

    }


    // =====================================================
    // SUBJECT SEARCH
    // =====================================================

    const subjectSearch =
        document.getElementById("subjectSearch");

    if (subjectSearch) {

        subjectSearch.addEventListener(
            "input",
            function () {

                filterSubjects(this.value);

            }
        );

    }


    function filterSubjects(searchText) {

        const text =
            searchText
                .toLowerCase()
                .trim();


        document
            .querySelectorAll(".subject-option")
            .forEach(function (option) {

                const content =
                    option.textContent.toLowerCase();

                option.style.display =
                    content.includes(text)
                        ? ""
                        : "none";

            });

    }


    // =====================================================
    // SUBJECT SELECT
    // =====================================================

    document
        .querySelectorAll(".subject-option")
        .forEach(function (option) {

            option.addEventListener(
                "click",
                function () {

                    const modal =
                        document.getElementById(
                            "subjectModal"
                        );

                    if (!modal) {
                        return;
                    }


                    const day =
                        modal.dataset.day;

                    const period =
                        parseInt(
                            modal.dataset.period
                        );


                    if (!day || !period) {
                        return;
                    }


                    // =========================================
                    // SUBJECT DURATION
                    // =========================================

                    const duration =
                        parseInt(
                            this.dataset.duration || "1"
                        );


                    const startPeriod =
                        period;

                    const endPeriod =
                        period + duration - 1;


                    // =========================================
                    // CHECK PERIOD LIMIT
                    // =========================================

                    if (endPeriod > 14) {

                        alert(
                            "This subject cannot fit in the selected time slot."
                        );

                        return;

                    }


                    // =========================================
                    // GET START SLOT
                    // =========================================

                    const firstSlot =
                        document.querySelector(
                            `.timetable-slot[data-day="${day}"][data-period="${startPeriod}"]`
                        );


                    if (!firstSlot) {
                        return;
                    }


                    // =========================================
                    // CREATE SUBJECT CARD
                    // =========================================

                    const classBox =
                        document.createElement("div");


                    classBox.className =
                        "scheduled-class";


                    // =========================================
                    // SAVE SUBJECT DATA
                    // =========================================

                    classBox.dataset.scheduleId = "";

                    classBox.dataset.resourceId =
                        this.dataset.resourceId || "";

                    classBox.dataset.code =
                        this.dataset.code || "";

                    classBox.dataset.name =
                        this.dataset.name || "";

                    classBox.dataset.section =
                        this.dataset.section || "";

                    classBox.dataset.sectionId =
                        this.dataset.sectionId || "";

                    classBox.dataset.lecturer =
                        this.dataset.lecturer || "";

                    classBox.dataset.lecturerId =
                        this.dataset.lecturerId || "";

                    classBox.dataset.delivery =
                        this.dataset.delivery || "";

                    classBox.dataset.classroom =
                        this.dataset.classroom || "";

                    classBox.dataset.classroomId =
                        this.dataset.classroomId || "";

                    classBox.dataset.day =
                        day;

                    classBox.dataset.period =
                        startPeriod;

                    classBox.dataset.duration =
                        duration;


                    // =========================================
                    // SUBJECT COLOUR
                    // =========================================

                    classBox.style.backgroundColor =
                        this.dataset.color ||
                        "#DCEEFF";


                    // =========================================
                    // SECTION NUMBER ONLY
                    // =========================================

                    const sectionNumber =
                        (this.dataset.section || "")
                            .replace(
                                /^Section\s*/i,
                                ""
                            )
                            .trim();


                    classBox.innerHTML = `
                        <strong>${sectionNumber}</strong>
                    `;


                    // =========================================
                    // DURATION CLASS
                    // =========================================

                    classBox.classList.add(
                        `duration-${duration}`
                    );


                    // =========================================
                    // STACK SUBJECTS
                    // =========================================
                    // If same period already has:
                    //
                    // 01
                    //
                    // New subject becomes:
                    //
                    // 01
                    // 02
                    //
                    // =========================================

                    const existingClasses =
                        firstSlot.querySelectorAll(
                            ".scheduled-class"
                        );


                    classBox.style.top =
                        `${2 + (existingClasses.length * 32)}px`;


                    // =========================================
                    // DO NOT CLEAR SLOT
                    // =========================================

                    firstSlot.appendChild(classBox);


                    // =========================================
                    // AUTO EXPAND TIMETABLE
                    // =========================================

                    updateTimetableRowHeight();


                    // =========================================
                    // CLOSE SUBJECT MODAL
                    // =========================================

                    if (typeof bootstrap !== "undefined") {

                        bootstrap.Modal
                            .getOrCreateInstance(modal)
                            .hide();

                    }

                }
            );

        });


    // =====================================================
    // CLASS DETAILS
    // =====================================================

    function openClassDetails(scheduleId) {

        const classBox =
            document.querySelector(
                `.scheduled-class[data-schedule-id="${scheduleId}"]`
            );


        if (classBox) {

            showClassDetailsFromBox(classBox);

            return;

        }


        const boxes =
            document.querySelectorAll(
                ".scheduled-class"
            );


        boxes.forEach(function (box) {

            if (!box.dataset.scheduleId) {

                if (box.dataset.code) {

                    showClassDetailsFromBox(box);

                }

            }

        });

    }


    function showClassDetailsFromBox(box) {

        const day =
            box.dataset.day ||
            findParentDay(box);


        const period =
            parseInt(
                box.dataset.period ||
                findParentPeriod(box)
            );


        const detailSubject =
            document.getElementById(
                "detailSubject"
            );

        if (detailSubject) {

            detailSubject.textContent =
                (box.dataset.code || "") +
                " - " +
                (box.dataset.name || "");

        }


        const detailSection =
            document.getElementById(
                "detailSection"
            );

        if (detailSection) {

            detailSection.textContent =
                "Section " +
                (box.dataset.section || "-");

        }


        const detailLecturer =
            document.getElementById(
                "detailLecturer"
            );

        if (detailLecturer) {

            detailLecturer.textContent =
                box.dataset.lecturer || "-";

        }


        const detailDay =
            document.getElementById(
                "detailDay"
            );

        if (detailDay) {

            detailDay.textContent =
                day || "-";

        }


        const detailTime =
            document.getElementById(
                "detailTime"
            );

        if (detailTime) {

            detailTime.textContent =
                getPeriodTime(period);

        }


        const detailDelivery =
            document.getElementById(
                "detailDelivery"
            );

        if (detailDelivery) {

            detailDelivery.textContent =
                box.dataset.delivery || "-";

        }


        const detailClassroom =
            document.getElementById(
                "detailClassroom"
            );

        if (detailClassroom) {

            detailClassroom.textContent =
                box.dataset.classroom ||
                "Online";

        }


        const modal =
            document.getElementById(
                "classDetailsModal"
            );


        if (!modal) {
            return;
        }


        if (typeof bootstrap !== "undefined") {

            bootstrap.Modal
                .getOrCreateInstance(modal)
                .show();

        }

    }


    function findParentDay(element) {

        const slot =
            element.closest(
                ".timetable-slot"
            );

        return slot
            ? slot.dataset.day
            : "";

    }


    function findParentPeriod(element) {

        const slot =
            element.closest(
                ".timetable-slot"
            );

        return slot
            ? slot.dataset.period
            : "";

    }


    // =====================================================
    // CLASS DETAILS CLICK
    // =====================================================
    // Clicking the actual card opens details.
    // Clicking the slot outside the card opens Add Subject.
    // =====================================================

    document.addEventListener(
        "click",
        function (event) {

            const classBox =
                event.target.closest(
                    ".scheduled-class"
                );


            if (!classBox) {
                return;
            }


            event.stopPropagation();


            showClassDetailsFromBox(
                classBox
            );

        }
    );


    // =====================================================
    // CALCULATE SUBJECT DURATION
    // =====================================================

    function calculateDuration(
        startTime,
        endTime
    ) {

        if (!startTime || !endTime) {
            return 1;
        }


        const startParts =
            String(startTime)
                .substring(0, 5)
                .split(":");


        const endParts =
            String(endTime)
                .substring(0, 5)
                .split(":");


        const startMinutes =
            parseInt(startParts[0]) * 60 +
            parseInt(startParts[1]);


        const endMinutes =
            parseInt(endParts[0]) * 60 +
            parseInt(endParts[1]);


        return Math.max(
            1,
            Math.round(
                (endMinutes - startMinutes) / 60
            )
        );

    }


    // =====================================================
    // CONVERT TIME TO PERIOD
    // =====================================================

    function timeToPeriod(time) {

        if (!time) {
            return 1;
        }


        const parts =
            String(time)
                .substring(0, 5)
                .split(":");


        const hour =
            parseInt(parts[0]);

        const minute =
            parseInt(parts[1]);


        const totalMinutes =
            hour * 60 + minute;


        return Math.floor(
            (totalMinutes - (8 * 60)) / 60
        ) + 1;

    }

    // =====================================================
// PERIOD TO TIME
// =====================================================

function periodToTime(period) {

    period =
        parseInt(period);


    const startMinutes =
        (8 * 60) +
        ((period - 1) * 60);


    const hour =
        Math.floor(
            startMinutes / 60
        );


    const minute =
        startMinutes % 60;


    return (
        String(hour).padStart(2, "0") +
        ":" +
        String(minute).padStart(2, "0") +
        ":00"
    );

}


    // =====================================================
    // LOAD EXISTING DATABASE SCHEDULES
    // =====================================================

    function loadExistingSchedules() {

        document
            .querySelectorAll(".schedule-data")
            .forEach(function (item) {

                const day =
                    item.dataset.day;

                const startTime =
                    item.dataset.start;

                const endTime =
                    item.dataset.end;


                // =========================================
                // START PERIOD
                // =========================================

                const startPeriod =
                    timeToPeriod(startTime);


                // =========================================
                // DURATION
                // =========================================

                const duration =
                    calculateDuration(
                        startTime,
                        endTime
                    );


                // =========================================
                // FIND SLOT
                // =========================================

                const slot =
                    document.querySelector(
                        `.timetable-slot[data-day="${day}"][data-period="${startPeriod}"]`
                    );


                if (!slot) {
                    return;
                }


                // =========================================
                // CREATE CARD
                // =========================================

                const classBox =
                    document.createElement("div");


                classBox.className =
                    "scheduled-class";


                // =========================================
                // SAVE DATA
                // =========================================

                classBox.dataset.scheduleId =
                    item.dataset.id || "";

                classBox.dataset.sectionId =
                    item.dataset.sectionId || "";

                classBox.dataset.code =
                    item.dataset.code || "";

                classBox.dataset.name =
                    item.dataset.name || "";

                classBox.dataset.section =
                    item.dataset.section || "";

                classBox.dataset.lecturer =
                    item.dataset.lecturer || "";
                    
                classBox.dataset.lecturerId =
                    item.dataset.lecturerId || "";

                classBox.dataset.delivery =
                    item.dataset.delivery || "";

                classBox.dataset.classroom =
                    item.dataset.classroom || "";

                classBox.dataset.classroomId =
                    item.dataset.classroomId || "";

                classBox.dataset.day =
                    day;

                classBox.dataset.period =
                    startPeriod;

                classBox.dataset.duration =
                    duration;


                // =========================================
                // SECTION NUMBER ONLY
                // =========================================

                const sectionNumber =
                    (item.dataset.section || "")
                        .replace(
                            /^Section\s*/i,
                            ""
                        )
                        .trim();


                classBox.innerHTML = `
                    <strong>${sectionNumber}</strong>
                `;


                // =========================================
                // SUBJECT COLOUR
                // =========================================

                classBox.style.backgroundColor =
                    item.dataset.color ||
                    "#DCEEFF";


                // =========================================
                // DURATION
                // =========================================

                classBox.classList.add(
                    `duration-${duration}`
                );


                // =========================================
                // STACK SAME START SLOT
                // =========================================

                const existingClasses =
                    slot.querySelectorAll(
                        ".scheduled-class"
                    );


                classBox.style.top =
                    `${2 + (existingClasses.length * 32)}px`;


                // =========================================
                // IMPORTANT:
                // DO NOT CLEAR THE SLOT
                // =========================================

                slot.appendChild(classBox);

            });


        // =============================================
        // AUTO EXPAND AFTER EXISTING CLASSES LOAD
        // =============================================

        updateTimetableRowHeight();

    }


    // =====================================================
    // AUTO EXPAND / COLLAPSE TIMETABLE
    // =====================================================
    //
    // Empty day:
    //     55px
    //
    // 1 subject:
    //     55px
    //
    // 2 subjects in same slot:
    //     87px
    //
    // 3 subjects:
    //     119px
    //
    // =====================================================

    function updateTimetableRowHeight() {

        document
            .querySelectorAll(".day-timetable")
            .forEach(function (table) {

                const row =
                    table.querySelector(
                        ".timetable-row"
                    );


                if (!row) {
                    return;
                }


                const slots =
                    table.querySelectorAll(
                        ".timetable-slot"
                    );


                let maxCards = 0;


                // =========================================
                // FIND MAXIMUM CARDS IN ONE PERIOD
                // =========================================

                slots.forEach(function (slot) {

                    const cardCount =
                        slot.querySelectorAll(
                            ".scheduled-class"
                        ).length;


                    maxCards =
                        Math.max(
                            maxCards,
                            cardCount
                        );

                });


                // =========================================
                // CALCULATE HEIGHT
                // =========================================
                //
                // Empty / 1 card = 55px
                // 2 cards = 87px
                // 3 cards = 119px
                // =========================================

                const rowHeight =
                    Math.max(
                        55,
                        55 +
                        (
                            Math.max(
                                0,
                                maxCards - 1
                            ) * 32
                        )
                    );


                // =========================================
                // APPLY HEIGHT TO WHOLE ROW
                // =========================================

                row.style.height =
                    rowHeight + "px";


                // =========================================
                // APPLY HEIGHT TO ALL SLOTS
                // =========================================

                slots.forEach(function (slot) {

                    slot.style.height =
                        rowHeight + "px";

                });

            });

    }

// =====================================================
// UPDATE TIMETABLE
// =====================================================

const saveTimetableBtn =
    document.getElementById("saveTimetableBtn");

if (saveTimetableBtn) {

    saveTimetableBtn.addEventListener(
        "click",
        async function () {

            // Get ALL classes currently displayed
            const classes =
                document.querySelectorAll(
                    ".scheduled-class"
                );


            // =========================================
            // CHECK
            // =========================================

            if (classes.length === 0) {

                alert(
                    "There are no classes in the timetable."
                );

                return;
            }


            // =========================================
            // DISABLE BUTTON
            // =========================================

            saveTimetableBtn.disabled = true;

            saveTimetableBtn.innerHTML = `
                <i class="bi bi-hourglass-split me-2"></i>
                Updating...
            `;


            let updatedCount = 0;
            let addedCount = 0;


            try {

                // =====================================
                // PROCESS ALL CLASSES
                // =====================================

                for (const classBox of classes) {

                    const scheduleId =
                        classBox.dataset.scheduleId || null;


                    const sectionId =
                        classBox.dataset.sectionId;


                    const lecturerId =
                        classBox.dataset.lecturerId;


                    const classroomId =
                        classBox.dataset.classroomId ||
                        null;


                    const deliveryMode =
                        classBox.dataset.delivery;


                    const day =
                        classBox.dataset.day;


                    const startPeriod =
                        parseInt(
                            classBox.dataset.period
                        );


                    const duration =
                        parseInt(
                            classBox.dataset.duration ||
                            "1"
                        );


                    // =================================
                    // VALIDATION
                    // =================================

                    if (!sectionId) {

                        throw new Error(
                            "Section information is missing."
                        );
                    }


                    if (!lecturerId) {

                        throw new Error(
                            "Lecturer information is missing."
                        );
                    }


                    if (!deliveryMode) {

                        throw new Error(
                            "Delivery mode is missing."
                        );
                    }


                    if (!day || !startPeriod) {

                        throw new Error(
                            "Day or period information is missing."
                        );
                    }


                    // =================================
                    // CONVERT PERIOD → TIME
                    // =================================

                    const startTime =
                        periodToTime(
                            startPeriod
                        );


                    const endTime =
                        periodToTime(
                            startPeriod + duration
                        );


                    // =================================
                    // SEND TO BACKEND
                    // =================================

                    const response =
                        await fetch(
                            "/admin/manage-timetable/save",
                            {
                                method: "POST",

                                headers: {
                                    "Content-Type":
                                        "application/json"
                                },

                                body: JSON.stringify({

                                    // IMPORTANT
                                    //
                                    // Existing class:
                                    // schedule_id = existing ID
                                    //
                                    // New class:
                                    // schedule_id = null

                                    schedule_id:
                                        scheduleId,

                                    section_id:
                                        sectionId,

                                    lecturer_id:
                                        lecturerId,

                                    classroom_id:
                                        classroomId,

                                    delivery_mode:
                                        deliveryMode,

                                    day:
                                        day,

                                    start_time:
                                        startTime,

                                    end_time:
                                        endTime
                                })
                            }
                        );


                    const result =
                        await response.json();


                    // =================================
                    // CHECK BACKEND RESPONSE
                    // =================================

                    if (
                        !response.ok ||
                        !result.success
                    ) {

                        throw new Error(
                            result.message ||
                            "Failed to update timetable."
                        );
                    }


                    // =================================
                    // COUNT
                    // =================================

                    if (scheduleId) {

                        updatedCount++;

                    } else {

                        addedCount++;

                    }


                    // =================================
                    // SAVE NEW DATABASE ID
                    // =================================

                    if (result.schedule_id) {

                        classBox.dataset.scheduleId =
                            result.schedule_id;
                    }

                }


                // =====================================
                // SUCCESS
                // =====================================

                alert(
                    "Timetable updated successfully.\n\n" +
                    "Existing classes updated: " +
                    updatedCount +
                    "\nNew classes added: " +
                    addedCount
                );


                // =====================================
                // RELOAD
                // =====================================

                window.location.reload();


            } catch (error) {

                console.error(
                    "Update timetable error:",
                    error
                );


                alert(
                    "Failed to update timetable:\n\n" +
                    error.message
                );


            } finally {

                saveTimetableBtn.disabled = false;

                saveTimetableBtn.innerHTML = `
                    <i class="bi bi-save me-2"></i>
                    Update Timetable
                `;
            }

        }
    );

}

    // =====================================================
    // INITIAL LOAD
    // =====================================================

    loadExistingSchedules();

});
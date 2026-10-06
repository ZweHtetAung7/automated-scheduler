# Next Version Notes

Ideas parked for after the current roadmap. Not designed yet.

## Estimate hours from the assignment description

**Idea:** the user pastes or uploads the assignment prompt (or it comes in through Canvas import), and the app suggests how many hours it will take.

**Rough approach**
- Use a language model to read the description and pull out the things that drive effort: type (essay, lab report, problem set, project, presentation), length (pages, word count, number of problems), research needed (sources required), group or solo, and deliverables.
- Turn those into hours with simple rules first (e.g. essay ≈ X hours per page plus research time), or let the model suggest a number with its reasoning.
- Show the estimate as a suggestion the user can accept or edit, never as a hidden value ("About 6 hours: 5 pages, 4 sources required").
- Adjust with the user's personal duration correction from logs (Phase 5), since "6 hours" for one student is 9 for another.
- Store the parsed details on the task so later estimates for the same course get better.

**Fits with:** Phase 3 (Canvas import brings the descriptions in), Phase 4 (same LLM setup as the chatbot) and Phase 5 (personal correction).

## Scan the course calendar as input

**Idea:** the user uploads a course calendar or syllabus schedule (PDF, image, web page, or a pasted table), and the app pulls out every dated item and adds it automatically.

**Rough approach**
- Read the file: text extraction for PDFs and web pages, OCR or a vision-capable language model for photos and screenshots.
- Use a language model to turn rows into structured items: class meetings, assignment due dates, exams and quizzes, readings per week, labs, holidays and no-class days.
- Pull grade weights from the syllabus grading section when it's in the same document.
- Show everything as a review list before saving ("Found 14 assignments, 3 exams, 2 holidays"), so the student can fix wrong dates or skip items.
- Handle relative dates ("Week 5, Tuesday") by asking for the semester start date once.
- Feed found items into the existing task and event data, so the scheduler, deadline warnings and exam prep mode use them like any other input.
- Pair with the hour-estimate feature above: each found assignment gets a suggested duration from its description.

**Fits with:** Phase 3 (Canvas import covers schools that use it; this covers PDFs and everything else) and Phase 4 (same LLM setup as the chatbot).

# Smart Civic Reporting Platform

## Getting Started

1. **Install Django & Pillow** (if not already installed in your Python environment):
   ```bash
   pip install django pillow
   ```

2. **Run Migrations**:
   ```bash
   python manage.py migrate
   ```

3. **Run the Development Server**:
   ```bash
   python manage.py runserver
   ```

4. **Open the Application**:
   Visit [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

---

## Planned Project Roadmap & Modules

### Overview
The central workflow of the platform:
1. **Module 2**: Citizen reports a civic issue
2. **Module 3**: Complaint is routed & managed by Department Admin
3. **Module 4**: Suitable worker is automatically assigned based on location/load
4. **Module 5**: Worker completes the repair task & uploads photo proof
5. **Module 6**: Admin verifies and closes the issue
6. **Module 7**: Notifications kept in sync for all actors
7. **Module 8**: Super Admin analyzes municipal performance & reports

---

### Module 2 — Civic Issue Reporting
**Simple meaning:** Allows citizens to report civic problems in their area digitally.
- **Workflow:**
  - Citizen notices a problem (e.g., large pothole near college gate).
  - Citizen fills out complaint form: selects Department, description, uploads photo, captures GPS coordinates/address.
  - Complaint is saved: system generates a unique complaint ID and records timestamp.
- **Features to build:**
  - Submit complaint form
  - Select issue category & department
  - Add description and photos
  - Capture GPS location (coordinates + readable address)
  - Generate unique Complaint ID
  - View complaint details, status, and attached images

---

### Module 3 — Complaint & Department Management
**Simple meaning:** Super Admin creates departments and assigns Department Admins. Complaints are automatically routed to the selected department's dashboard.
- **Workflow:**
  - Super Admin creates departments and assigns Department Admins.
  - Citizen complaint reaches the selected department admin dashboard.
  - Department Admin reviews complaint, sets priority, monitors overdue items, and assigns/reassigns workers.
- **Features to build:**
  - Super Admin: create, update, and manage departments & Department Admin accounts.
  - Department routing: citizen selects department, complaint is directed to that department.
  - Department Admin dashboard: view/manage complaints scoped exclusively to their department.
  - Search, filter, and set complaint priorities (Low, Medium, High, Critical).
  - Manual worker assignment/reassignment.
  - Monitor pending and overdue complaints.
  - Maintain complaint status and assignment history audit log.

---

### Module 4 — Automated Worker Assignment
**Simple meaning:** Instead of manual dispatch, the system automatically finds and assigns the best-suited worker based on proximity and workload.
- **Workflow:**
  - When a complaint arrives, system checks eligible workers in that department.
  - System calculates distance (using Haversine formula) and checks worker availability & task queue.
  - Nearest available worker with lowest workload is automatically assigned and notified.
- **Features to build:**
  - Eligible worker identification by department.
  - Distance calculation using Haversine formula based on coordinates.
  - Workload balance & availability checker.
  - Automated assignment engine.
  - Fallback handling when no workers are available.
  - Reassignment tracking and audit history.

---

### Module 5 — Worker Management
**Simple meaning:** Workers view tasks assigned to them, manage their status, and upload repair proof.
- **Workflow:**
  - Worker logs in and views assigned complaints on their dashboard.
  - Worker accepts/declines task and marks status as "In Progress".
  - Worker uploads "after-repair" photograph and marks task as "Completed".
- **Features to build:**
  - Worker profile and availability status toggles.
  - Assigned complaint dashboard with location, images, and description.
  - Task acceptance and progress status updates.
  - Upload completion proof (after-repair photos & notes).
  - Task completion submission and history log.

---

### Module 6 — Verification & Resolution
**Simple meaning:** Administrators verify worker proof before marking complaints as officially closed.
- **Workflow:**
  - Worker submits completion proof photo.
  - Department Admin inspects the photo evidence.
  - If approved: complaint is marked as verified & closed.
  - If rejected: reason is provided, and the task returns to the worker for further repair.
- **Features to build:**
  - Completed tasks awaiting verification queue.
  - Before vs. After photographic evidence comparison.
  - Admin Approve or Reject action with mandatory rejection reasons.
  - Auto-reopening or reassigning rejected complaints.
  - Closure verification audit trail.

---

### Module 7 — Notifications
**Simple meaning:** Real-time in-app alerts and notifications keeping citizens, workers, and administrators updated.
- **Workflow:**
  - Citizen notified upon submission, status change, and final resolution.
  - Worker notified upon new task assignment.
  - Admin alerted on overdue complaints and new submissions.
- **Features to build:**
  - In-app notification center (bell icon dropdown).
  - Notification models with read/unread tracking.
  - Alerts for submission, assignment, progress, verification, rejection, and resolution.
  - Optional email alert integration.

---

### Module 8 — Super Admin, Analytics & Reporting
**Simple meaning:** High-level municipal dashboard to evaluate city-wide civic performance and generate reports.
- **Workflow:**
  - Super Admin inspects system-wide stats (total complaints, pending, resolved, in progress).
  - Breakdown by department, category, and average resolution time.
  - Export data for council meetings and audits.
- **Features to build:**
  - System-wide executive dashboard with key metrics and counters.
  - Category and department volume breakdown charts.
  - Average resolution time tracking and SLA breach alerts.
  - Worker and department performance rating indicators.
  - Export reports to CSV or PDF.

---

## Existing UI Components Converted:
- **Header**: Responsive navigation bar with branding and login/register actions.
- **HeroSection**: Animated RetroGrid canvas, dynamic gradient badge, typography, and dual CTAs.
- **IssueTrackingSection**: Interactive 3D Perspective Flip Card (Kanban board on front, detailed live submission view with maps/media on back).
- **AdminManagementSection**: Operational dashboard preview and customized status perspective columns.
- **Features**: 4-column capability cards with hover effects and report counters.
- **CTA**: Step-by-step civic reporting workflow with connector lines.
- **Footer**: Brand signature and copyright notice.

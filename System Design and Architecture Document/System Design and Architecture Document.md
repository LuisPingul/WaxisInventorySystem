#   
  
# System Design and Architecture Document  
**Project Title:** Waxi's Smart Inventory & AI-Powered Predictive Procurement System **Client:** SND FOODS INTERNATIONAL INC. (Waxi's) **Target SDG:** SDG 12 - Responsible Consumption & Production  
## 1. Executive Summary  
The proposed system transitions Waxi's from a manual, reactive inventory tracking method (Google Sheets) into an automated, proactive web-based ecosystem. By creating dedicated interfaces for both Kitchen Staff and Operations Management, the system captures stock depletion in real-time. Furthermore, it introduces an AI-driven Predictive Procurement engine that analyzes historical usage to forecast ingredient shortages and automate supplier communication.  
## 2. High-Level System Architecture  
The system follows a unified Django monolith (Model-View-Template) architecture, leveraging Django's full-stack capabilities for both frontend rendering and backend logic to ensure maintainability, rapid development, and scalability at Waxi's single-site scale.  
## A. Frontend (Client-Side)  
* **Framework:** Django Templates (Server-Rendered) + HTMX for reactive partial updates (no SPA).  
* **Styling:** Bootstrap 5.3.3 + Bootstrap Icons (responsive grid, touch-friendly `form-control-lg` targets); complements the Django ecosystem.  
* **Design Philosophy:** Mobile/Tablet-first for the Kitchen Hub (48dp touch targets, large deduction form); Desktop-optimized for the Admin Dashboard (data-heavy tables and charts).  
* **Data Visualization:** Chart.js via CDN for dynamic dashboard analytics (Storage Distribution, turnover), rendered from Django context `json_script`.  
* **Interactivity:** HTMX `hx-get` with `delay:300ms` for kitchen search autocomplete, gracefully degrading to standard GET filter when JS disabled.  
## B. Backend (Server-Side)  
* **Framework:** Django (Python) 5.2  
* **API Architecture:** Django Views handling form POST/GET between template frontend and PostgreSQL via ORM; no decoupled SPA JSON required. HTMX partials return HTML fragments (`_results.html`) rather than JSON.  
* **AI/ML Engine:** * *Forecasting:* Pure-Python rolling-average time-series (30-day `StockTransaction` aggregation) with optional `Prophet` upgrade path; analyzes `Activity_Logs` (`StockTransaction`) to predict depletion dates and auto-generates `AI_Procurement_Alerts`. Nightly `manage.py compute_forecasts` via system cron (`0 2 * * *`).  
    * *LLM Integration:* `google-generativeai` (Gemini 1.5 Flash) triggered from Django view `procurement/services.py:generate_po_email()` using `GEMINI_API_KEY` env to auto-generate context-aware Purchase Order (PO) emails routed to `Supplier.email`.  
## C. Database (Data Layer)  
* **DBMS:** PostgreSQL (Relational Database)  
* **Reasoning:** A relational database is required to strictly enforce data integrity between inventory items, suppliers, active purchase orders, and historical logs.  
## 3. Core System Modules  
## Module 1: Kitchen Hub (Staff Interface)  
A touch-optimized tablet interface located in the kitchen.  
* **Function:** Allows staff to quickly search for raw ingredients and input exact numerical deductions as they are consumed during shifts.  
* **Architecture Impact:** Every deduction triggers a POST request to the backend, immediately updating the Inventory_Items table and writing a timestamped record to the Activity_Logs.  
## Module 2: Command Dashboard (Admin Interface)  
The central hub for the Operations Manager.  
* **Function:** Displays high-level analytics, including Total SKUs, Critical/Low Stock alerts, Pending Deliveries, Storage Distribution (Frozen, Chilled, Dry), and a live movement ticker.  
* **AI Integration:** Features an "AI Executive Summary" generator that reads the current state of the database and provides a real-time operational health report.  
## Module 3: PO Manager & Predictive Procurement  
The core innovation of the Capstone project.  
* **Function:** Instead of manually checking stock, the system generates proactive alerts (e.g., "Expected to run out of Chicken Wings by Saturday").  
* **Workflow:** 1. AI flags an item based on reorder points and velocity. 2. Manager reviews the suggested restock quantity. 3. System uses LLM to draft a formal email to the assigned supplier. 4. Once dispatched, the order is tracked in the "Active Purchase Orders" pipeline until marked as "Delivered" (which automatically restocks the inventory).  
## Module 4: Supplier Directory (CRUD)  
* **Function:** A complete management tab for vendor profiles.  
* **Architecture Impact:** Dynamically feeds the PO Manager dropdowns, ensuring purchase orders are routed to the correct external vendor emails.  
## 4. Data Architecture (Entity Relationship summary)  
The PostgreSQL database is normalized and relies on the following core entities and relationships:  
1. **Users**: Manages authentication and role-based access (Admin vs. Staff).  
2. **Inventory_Items**: The master catalog of ingredients (stock level, reorder point, storage type).  
3. **Suppliers**: Directory of vendors (contact info, categories supplied).  
4. **Purchase_Orders**: Tracks active orders. *Relates to* Inventory_Items (what is being ordered) and Suppliers (who is fulfilling it).  
5. **Activity_Logs**: The audit trail. *Relates to* Inventory_Items (what moved) and Users (who moved it). Used extensively by the AI for forecasting.  
6. **AI_Procurement_Alerts**: Stores pending predictive suggestions before human approval.  
## 5. Security & Constraints  
* **Role-Based Access Control (RBAC):** Strict isolation between the Kitchen Hub (write-only for deductions) and the Admin Portal (full CRUD and analytical access).  
* **Referential Integrity:** Enforced at the SQL level (e.g., a Purchase_Order cannot be created for an Inventory_Item that does not exist).  

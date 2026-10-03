-- Schema snapshot only; no rows. Exported 2026-09-27T10:39:13+07:00
-- Migration 0008; includes indexes and triggers.

CREATE TABLE alembic_version (
	version_num VARCHAR(32) NOT NULL, 
	CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

CREATE TABLE articles (
	number VARCHAR(40) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	category_id INTEGER NOT NULL, 
	summary TEXT, 
	problem TEXT, 
	symptoms TEXT, 
	cause TEXT, 
	resolution TEXT NOT NULL, 
	commands TEXT, 
	notes TEXT, 
	tags TEXT, 
	author_id INTEGER NOT NULL, 
	status_id INTEGER NOT NULL, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (number), 
	FOREIGN KEY(category_id) REFERENCES master_data (id), 
	FOREIGN KEY(author_id) REFERENCES users (id), 
	FOREIGN KEY(status_id) REFERENCES master_data (id)
);

CREATE TABLE asset_operations (
	number VARCHAR(40) NOT NULL, 
	asset_id INTEGER NOT NULL, 
	operation_type VARCHAR(30) NOT NULL, 
	from_entity_type VARCHAR(30), 
	from_entity_id INTEGER, 
	to_entity_type VARCHAR(30), 
	to_entity_id INTEGER, 
	operation_date DATETIME NOT NULL, 
	condition_before TEXT, 
	condition_after TEXT, 
	performed_by INTEGER NOT NULL, 
	reason TEXT, 
	note TEXT, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, before_state JSON, after_state JSON, source_ref VARCHAR(120), 
	PRIMARY KEY (id), 
	FOREIGN KEY(asset_id) REFERENCES assets (id), 
	FOREIGN KEY(performed_by) REFERENCES users (id), 
	UNIQUE (number)
);

CREATE TABLE asset_types (
	name VARCHAR(100) NOT NULL, 
	prefix VARCHAR(20) NOT NULL, 
	track_location BOOLEAN NOT NULL, 
	allow_assignment BOOLEAN NOT NULL, 
	track_network BOOLEAN NOT NULL, 
	allow_ticket BOOLEAN NOT NULL, 
	track_maintenance BOOLEAN NOT NULL, 
	has_ports BOOLEAN NOT NULL, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, track_serial BOOLEAN DEFAULT 1 NOT NULL, allow_station BOOLEAN DEFAULT 1 NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE assets (
	code VARCHAR(40) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	type_id INTEGER NOT NULL, 
	status_id INTEGER NOT NULL, 
	brand VARCHAR(100), 
	model VARCHAR(100), 
	serial VARCHAR(150), 
	purchase_date DATETIME, 
	warranty_expiry DATETIME, 
	vendor VARCHAR(150), 
	cost NUMERIC(14, 2), 
	description TEXT, 
	notes TEXT, 
	photo TEXT, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, received_date DATE, handover_date DATE, warehouse_id INTEGER REFERENCES warehouses(id), current_status VARCHAR(20) DEFAULT 'AVAILABLE' NOT NULL, current_location_id INTEGER REFERENCES locations(id), current_assignee_id INTEGER REFERENCES users(id), 
	PRIMARY KEY (id), 
	UNIQUE (code), 
	FOREIGN KEY(type_id) REFERENCES asset_types (id), 
	FOREIGN KEY(status_id) REFERENCES master_data (id), 
	UNIQUE (serial)
);

CREATE TABLE assignments (
	asset_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	department VARCHAR(100), 
	assigned_by INTEGER NOT NULL, 
	expected_return DATETIME, 
	returned_at DATETIME, 
	condition_out TEXT NOT NULL, 
	condition_in TEXT, 
	note TEXT, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(asset_id) REFERENCES assets (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(assigned_by) REFERENCES users (id)
);

CREATE TABLE attachments (
	ticket_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	storage_key VARCHAR(100) NOT NULL, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	UNIQUE (storage_key)
);

CREATE TABLE audit_logs (
	id INTEGER NOT NULL, 
	user_id INTEGER, 
	action VARCHAR(80) NOT NULL, 
	object_type VARCHAR(80) NOT NULL, 
	object_id INTEGER NOT NULL, 
	old_value JSON, 
	new_value JSON, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE counters (
	"key" VARCHAR(40) NOT NULL, 
	value INTEGER NOT NULL, 
	PRIMARY KEY ("key")
);

CREATE TABLE interfaces (
	asset_id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	mac VARCHAR(17) NOT NULL, 
	hostname VARCHAR(150), 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(asset_id) REFERENCES assets (id), 
	UNIQUE (mac)
);

CREATE TABLE inventory_items (
	code VARCHAR(40) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	category VARCHAR(80) NOT NULL, 
	unit VARCHAR(30) NOT NULL, 
	quantity NUMERIC(14, 3) NOT NULL, 
	minimum_stock NUMERIC(14, 3) NOT NULL, 
	warehouse_id INTEGER NOT NULL, 
	bin_shelf VARCHAR(80), 
	description TEXT, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id), 
	UNIQUE (code)
);

CREATE TABLE inventory_transactions (
	number VARCHAR(40) NOT NULL, 
	transaction_type VARCHAR(20) NOT NULL, 
	warehouse_id INTEGER NOT NULL, 
	asset_id INTEGER, 
	item_id INTEGER, 
	quantity NUMERIC(14, 3) NOT NULL, 
	transaction_date DATETIME NOT NULL, 
	source_vendor VARCHAR(150), 
	condition TEXT, 
	performed_by INTEGER NOT NULL, 
	note TEXT, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, recipient_user_id INTEGER REFERENCES users(id), recipient_location_id INTEGER REFERENCES locations(id), 
	PRIMARY KEY (id), 
	FOREIGN KEY(warehouse_id) REFERENCES warehouses (id), 
	FOREIGN KEY(asset_id) REFERENCES assets (id), 
	FOREIGN KEY(item_id) REFERENCES inventory_items (id), 
	FOREIGN KEY(performed_by) REFERENCES users (id), 
	UNIQUE (number)
);

CREATE TABLE ip_addresses (
	address VARCHAR(60) NOT NULL, 
	interface_id INTEGER, 
	subnet_id INTEGER NOT NULL, 
	status_id INTEGER NOT NULL, 
	description TEXT, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (address), 
	FOREIGN KEY(interface_id) REFERENCES interfaces (id), 
	FOREIGN KEY(subnet_id) REFERENCES subnets (id), 
	FOREIGN KEY(status_id) REFERENCES master_data (id)
);

CREATE TABLE location_history (
	asset_id INTEGER NOT NULL, 
	from_location_id INTEGER, 
	location_id INTEGER NOT NULL, 
	technician_id INTEGER NOT NULL, 
	reason TEXT NOT NULL, 
	note TEXT, 
	ended_at DATETIME, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(asset_id) REFERENCES assets (id), 
	FOREIGN KEY(from_location_id) REFERENCES locations (id), 
	FOREIGN KEY(location_id) REFERENCES locations (id), 
	FOREIGN KEY(technician_id) REFERENCES users (id)
);

CREATE TABLE locations (
	name VARCHAR(100) NOT NULL, 
	kind VARCHAR(30) NOT NULL, 
	parent_id INTEGER, 
	description TEXT, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, active BOOLEAN DEFAULT 1 NOT NULL, physical_location VARCHAR(200), department VARCHAR(100), floor VARCHAR(80), area VARCHAR(80), photo TEXT, 
	PRIMARY KEY (id), 
	UNIQUE (parent_id, name), 
	FOREIGN KEY(parent_id) REFERENCES locations (id)
);

CREATE TABLE "maintenance" (
	number VARCHAR(40) NOT NULL, 
	asset_id INTEGER NOT NULL, 
	type_id INTEGER NOT NULL, 
	status_id INTEGER NOT NULL, 
	problem TEXT NOT NULL, 
	diagnosis TEXT, 
	action_taken TEXT, 
	technician_id INTEGER NOT NULL, 
	start_at DATETIME NOT NULL, 
	due_at DATETIME, 
	end_at DATETIME, 
	vendor VARCHAR(150), 
	cost NUMERIC(14, 2), 
	parts_replaced TEXT, 
	note TEXT, 
	previous_status_id INTEGER, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT fk_maintenance_previous_status_id_master_data FOREIGN KEY(previous_status_id) REFERENCES master_data (id), 
	CONSTRAINT fk_maintenance_status_id_master_data FOREIGN KEY(status_id) REFERENCES master_data (id), 
	CONSTRAINT fk_maintenance_type_id_master_data FOREIGN KEY(type_id) REFERENCES master_data (id), 
	CONSTRAINT fk_maintenance_asset_id_assets FOREIGN KEY(asset_id) REFERENCES assets (id), 
	CONSTRAINT fk_maintenance_technician_id_users FOREIGN KEY(technician_id) REFERENCES users (id), 
	UNIQUE (number)
);

CREATE TABLE master_data (
	"group" VARCHAR(60) NOT NULL, 
	code VARCHAR(60) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	color VARCHAR(30) NOT NULL, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE ("group", code)
);

CREATE TABLE subnets (
	cidr VARCHAR(60) NOT NULL, 
	gateway VARCHAR(60), 
	dns VARCHAR(200), 
	vlan_id INTEGER NOT NULL, 
	site_id INTEGER NOT NULL, 
	description TEXT, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (cidr), 
	FOREIGN KEY(vlan_id) REFERENCES vlans (id), 
	FOREIGN KEY(site_id) REFERENCES locations (id)
);

CREATE TABLE switch_ports (
	switch_id INTEGER NOT NULL, 
	name VARCHAR(40) NOT NULL, 
	mode_id INTEGER NOT NULL, 
	native_vlan_id INTEGER, 
	tagged_vlans JSON NOT NULL, 
	connected_asset_id INTEGER, 
	status_id INTEGER NOT NULL, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (switch_id, name), 
	UNIQUE (connected_asset_id), 
	FOREIGN KEY(switch_id) REFERENCES assets (id), 
	FOREIGN KEY(mode_id) REFERENCES master_data (id), 
	FOREIGN KEY(native_vlan_id) REFERENCES vlans (id), 
	FOREIGN KEY(connected_asset_id) REFERENCES assets (id), 
	FOREIGN KEY(status_id) REFERENCES master_data (id)
);

CREATE TABLE ticket_activities (
	ticket_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	kind VARCHAR(40) NOT NULL, 
	body TEXT NOT NULL, 
	internal BOOLEAN NOT NULL, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE ticket_articles (
	ticket_id INTEGER NOT NULL, 
	article_id INTEGER NOT NULL, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (ticket_id, article_id), 
	FOREIGN KEY(ticket_id) REFERENCES tickets (id), 
	FOREIGN KEY(article_id) REFERENCES articles (id)
);

CREATE TABLE tickets (
	number VARCHAR(40) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	description TEXT NOT NULL, 
	category_id INTEGER NOT NULL, 
	subcategory VARCHAR(100), 
	priority_id INTEGER NOT NULL, 
	status_id INTEGER NOT NULL, 
	asset_id INTEGER, 
	location_id INTEGER, 
	reporter_id INTEGER NOT NULL, 
	technician_id INTEGER, 
	due_at DATETIME, 
	resolved_at DATETIME, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (number), 
	FOREIGN KEY(category_id) REFERENCES master_data (id), 
	FOREIGN KEY(priority_id) REFERENCES master_data (id), 
	FOREIGN KEY(status_id) REFERENCES master_data (id), 
	FOREIGN KEY(asset_id) REFERENCES assets (id), 
	FOREIGN KEY(location_id) REFERENCES locations (id), 
	FOREIGN KEY(reporter_id) REFERENCES users (id), 
	FOREIGN KEY(technician_id) REFERENCES users (id)
);

CREATE TABLE users (
	username VARCHAR(100) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	password_hash TEXT NOT NULL, 
	role VARCHAR(30) NOT NULL, 
	department VARCHAR(100), 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (username)
);

CREATE TABLE vlans (
	tag INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	site_id INTEGER NOT NULL, 
	description TEXT, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (site_id, tag), 
	FOREIGN KEY(site_id) REFERENCES locations (id)
);

CREATE TABLE warehouses (
	code VARCHAR(40) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	location_id INTEGER NOT NULL, 
	description TEXT, 
	id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	archived BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(location_id) REFERENCES locations (id), 
	UNIQUE (code)
);

CREATE UNIQUE INDEX uq_active_assignment ON assignments (asset_id) WHERE returned_at IS NULL;

CREATE UNIQUE INDEX uq_asset_event_source ON asset_operations (source_ref);

CREATE UNIQUE INDEX uq_current_location ON location_history (asset_id) WHERE ended_at IS NULL;

CREATE TRIGGER ck_asset_status_insert BEFORE INSERT ON assets WHEN NEW.current_status NOT IN ('AVAILABLE','IN_USE','MAINTENANCE','RETIRED','DISPOSED') OR NEW.current_status IS NULL BEGIN SELECT RAISE(ABORT, 'Invalid asset status'); END;

CREATE TRIGGER ck_asset_status_update BEFORE UPDATE ON assets WHEN NEW.current_status NOT IN ('AVAILABLE','IN_USE','MAINTENANCE','RETIRED','DISPOSED') OR NEW.current_status IS NULL BEGIN SELECT RAISE(ABORT, 'Invalid asset status'); END;

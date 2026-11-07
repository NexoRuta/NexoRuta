const admin = db.getSiblingDB("admin");
const rootUser = process.env.MONGO_ROOT_USERNAME;
const rootPassword = process.env.MONGO_ROOT_PASSWORD;

if (!rootUser || !rootPassword) {
  throw new Error("MongoDB root credentials are required to reconcile runtime users.");
}

const authenticated = admin.auth(rootUser, rootPassword);
if (authenticated !== 1 && authenticated?.ok !== 1) {
  throw new Error("MongoDB root authentication failed while reconciling runtime users.");
}

const database = db.getSiblingDB("nexoruta");
const apiPassword = process.env.MONGO_API_PASSWORD;
const workerPassword = process.env.MONGO_WORKER_PASSWORD;
if (!apiPassword || !workerPassword) {
  throw new Error("MongoDB application credentials are required to reconcile runtime users.");
}

function reconcileRole(name, privileges) {
  const role = database.getRole(name, { showPrivileges: true });
  const definition = { privileges, roles: [] };
  if (role === null) {
    database.createRole({ role: name, ...definition });
  } else {
    database.updateRole(name, definition);
  }
}

function reconcileUser(name, password, roles) {
  const definition = { pwd: password, roles };
  if (database.getUser(name) === null) {
    database.createUser({ user: name, ...definition });
  } else {
    database.updateUser(name, definition);
  }
}

reconcileRole("nexorutaOperationalHistoryReaderV1", [{
  resource: { db: "nexoruta", collection: "operational_history_v1" },
  actions: ["find"]
}]);

reconcileRole("nexorutaOperationalHistoryWorkerV1", [
  {
    resource: { db: "nexoruta", collection: "" },
    actions: ["listCollections", "createCollection"]
  },
  {
    resource: { db: "nexoruta", collection: "operational_history_v1" },
    actions: ["find", "insert", "createIndex"]
  },
  {
    resource: { db: "nexoruta", collection: "PasswordRecoveryRequested" },
    actions: ["find", "insert", "createIndex"]
  }
]);

reconcileUser("nexoruta_api", apiPassword, [
  { role: "nexorutaOperationalHistoryReaderV1", db: "nexoruta" }
]);
reconcileUser("nexoruta_worker", workerPassword, [
  { role: "nexorutaOperationalHistoryWorkerV1", db: "nexoruta" }
]);

print("MongoDB operational runtime roles are ready.");

let token = "ERROR";

const request = indexedDB.open("firebase-app-check-database");

async function getToken() {
    return new Promise((resolve, reject) => {
        request.onsuccess = function(event) {
            const db = event.target.result;
            const transaction = db.transaction("firebase-app-check-store", "readonly");
            const store = transaction.objectStore("firebase-app-check-store");
            const getAllRequest = store.getAll();

            getAllRequest.onsuccess = function() {
                const records = getAllRequest.result;
                if (records.length > 0 && records[0].value && records[0].value.token) {
                    token = records[0].value.token;
                    console.log("Firebase App Check Token:\n", token);
                    resolve(token); // Resolve the promise with the token
                } else {
                    console.log("Token not found in IndexedDB.");
                    resolve(null); // Resolve with null if no token is found
                }
            };

            getAllRequest.onerror = function() {
                console.error("Error retrieving data from IndexedDB.");
                reject("Error retrieving data from IndexedDB.");
            };
        };

        request.onerror = function() {
            console.error("Failed to open IndexedDB.");
            reject("Failed to open IndexedDB.");
        };
    });
}

// Call the function and handle the promise
getToken().then((token) => {
    console.log("Token received: ", token);
}).catch((error) => {
    console.error("Error occurred:", error);
});

return getToken();

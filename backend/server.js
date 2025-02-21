import express from "express";
import fs from "fs";
import cors from "cors";

const app = express();
const PORT = 5000;

// Middleware
app.use(express.json());
app.use(cors());

// API to save username
app.post("/signup", (req, res) => {
  const { username } = req.body;

  if (!username || username.trim() === "") {
    return res.status(400).json({ message: "Username cannot be empty" });
  }

  //get the MAC address

  //append the mac address to the username

  //check if the username + addy has been saved before --> error if yes///

  try {
    fs.appendFileSync("usernames.txt", username + "\n"); // Save username
    res.json({ message: "Username saved successfully!" });
  } catch (error) {
    console.error("Error saving username:", error);
    res.status(500).json({ message: "Failed to save username" });
  }
});

app.get("/users", (req, res) => {  
    try {
        //read saved usernames...
        users = fs.readFileSync("usernames.txt")
        res.json({ message: {users} });
    } catch (error) {
      console.error("Error reading saved usernames:", error);
      res.status(500).json({ message: "Failed to read usernames" });
    }
  });


app.get("/whoAmI", (req, res) => {
try {
    //get my username:
    username = fs.readFileSync("identity.txt");
    if(username == ""){
        username = "guest"
    }
} catch (error) {
    console.error("Error retrieving username:", error);
    res.status(500).json({ message: "Failed to save username" });
}
});
// Start server
app.listen(PORT, () => console.log(`\n\nServer running on http://localhost:${PORT}`));

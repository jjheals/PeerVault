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
    fs.appendFileSync("identity.txt", username + "\n"); // Save username

    res.json({ message: "Username saved successfully!" });
  } catch (error) {
    console.error("Error saving username:", error);
    res.status(500).json({ message: "Failed to save username" });
  }
});

app.get("/users", (req, res) => {  
  const users = fs.readFileSync("usernames.txt", { encoding: "utf-8", flag: "r" });
  var user_array = users.split("\n");
  user_array.pop();
  res.json({users: user_array})
  });


app.get("/whoAmI", (req, res) => {
  try {
      //get my username:
      var username = "";

      username = fs.readFileSync("identity.txt",
        { encoding: 'utf-8', flag: 'r'},
        function (err, username) {
          if (err)
              console.log(err);
          });

      if(username == ""){
          res.json({ identity: "Guest" });
      }
      res.json({ identity: username });

  } catch (error) {
      res.json({ identity: "Guest" });
  }
});

app.get("/uploadData", (req, res) => {
  res.status(200);
});


// Start server
app.listen(PORT, () => console.log(`\n\nServer running on http://localhost:${PORT}`));

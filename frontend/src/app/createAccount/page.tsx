'use client';

import React from "react";
import { Model } from "@/model";
import { useRouter} from "next/navigation";
import fs from "fs";
import axios from "axios";

const PORT = 4303;

const instance = axios.create({
  baseURL:
    "http://localhost:" + PORT.toString(),
});

export default function Home() {
    const [model, setModel] = React.useState(new Model())
    const [redraw, forceRedraw] = React.useState(0);
    const [username, setUsername] = React.useState("");

    function refresh() {
        forceRedraw(redraw + 1);
    }

    const router = useRouter();

    const handleSignup = async () => {
        if (!username.trim()) 
        {
          alert("Username cannot be empty!");
          return;
        }
    
        try 
        {
          // instance
          // .post("/signup", {
          //   username: username
          // })
          // .then(function(response) {
          //   const data = response.data;
          //   alert(data.message);
          //   setUsername("");
          // })
          // .catch(function (error) {
          //   console.log(error);
          // });
          
          const response = await fetch("http://localhost:4303/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username }),
          });
    
          console.log("sent message");
          const data = await response.json();
          console.log("recvd. response: ", data);

          alert(data.message);
          setUsername("");
        } 
        catch (error)
        {
          console.error("Error:", error);
          alert("Failed to save username.");
        }

        router.push('/');
      };

    return (
      <div className="header">
        <div className="header-row">
          <div className="titleText">Create Account</div>
          <div className="header-options-row">
            <button onClick={()=> router.push("/")}>
              <div className="header-button-text-option-one">Back</div>
            </button>
            <hr className="h-px my-3 bg-gray-200 border-0 dark:bg-gray-700"></hr>
          </div>
        </div>

        <div>
            <div className="subtitleText">Signup</div>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Enter username" />
            <button className="button" onClick={handleSignup}>Sign Up</button>
        </div>


      </div>
    )
}
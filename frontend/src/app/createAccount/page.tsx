'use client';

import React from "react";
import { Model } from "@/model";
import { useRouter} from "next/navigation";
import fs from "fs";
import axios from "axios";

const PORT = 8000;

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
          React.useEffect(() =>{
            instance
            .post("/signup", { data: username})
            .then(function (response){
                console.log(response);
                alert(response.data.message);
                setUsername(username);
              });
        router.push('/');
      });
    }

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
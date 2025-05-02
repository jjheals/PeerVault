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
    const [passphrase, setPassphrase] = React.useState("");
    const [storage, setStorage] = React.useState("");
    const [path, setPath] = React.useState("");


    function refresh() {
        forceRedraw(redraw + 1);
    }

    const router = useRouter();

    const handleSignup = async () => {
      if (!username.trim() ||!passphrase.trim() || !storage.trim()|| !path.trim()) {
          alert("All Fields are required!");
          return;
      }
      try {
        const response = await instance.post("/ui/signup", { common_name: username,
                                                              passphrase: passphrase,
                                                              allocated_storage: storage,
                                                              peer_storage_path: path });

        alert("signup successful");
      } catch (error) {
        const statuscode = error.response.status
        switch (statuscode){
          case 400:
            alert("Bad Request. There is missing or misformated data")
          case 409:
            alert("A user already exists for this machine")
          default:
            alert("Signup failed. Please try again.");
        }

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
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" />
            <input type="text" value={passphrase} onChange={(e) => setPassphrase(e.target.value)} placeholder="Passphrase" />
            <input type="int" value={storage} onChange={(e) => setStorage(e.target.value)} placeholder="Storage Amount GB" />
            <input type="text" value={path} onChange={(e) => setPath(e.target.value)} placeholder="Storage Path" />
            <button className="button" onClick={handleSignup}>Sign Up</button>
        </div>
      </div>
    )
}
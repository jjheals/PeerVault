'use client'; //needed to handle site events (clicks / events / interactions)

import React, {Suspense} from "react";
import axios from "axios";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";


const PORT = 8000;
const instance = axios.create({
baseURL:
"http://localhost:" + PORT.toString(),
});

export default function Home() { 
    const router = useRouter();
    const [passphrase, setPassphrase] = React.useState("");
    const [newPassphrase, setNewPassphrase] = React.useState("");

    const handleChange = async () => {
        if (!passphrase.trim()) {
            alert("All Fields are required!");
            return;
        }
        try {
            const response = await instance.post("/changepassphrase", {passphrase: passphrase});
            alert("Passphrase successfully changed!");
        } catch (error) {
            console.error("Passphrase change failed:", error);
            alert("Passphrase change failed. Please try again.");
        }
        router.push('/');
    };

    return (
    <div>
        <div className="header">
            <div className="header-row">
            <div className="titleText">Change Passphrase:</div>
            <div className="header-options-row">

                <div className="icon-padding"></div>
                <button onClick={()=> router.push("/")}>
                    <div className="hover" title="Return Home">
                        <Image
                        className="dark"
                        src="/home-1-svgrepo-com.svg"
                        alt="home icon"
                        width={50}
                        height={50}
                        />
                    </div>
                </button>
            </div> 
        </div>
            <div className="subtitleText">Signup</div>
            <input type="text" value={passphrase} onChange={(e) => setPassphrase(e.target.value)} placeholder="Current Passphrase" />
            <input type="text" value={newPassphrase} onChange={(e) => setNewPassphrase(e.target.value)} placeholder="New Passphrase" />
            <div className="button" onClick={handleChange}>Change Passphrase</div>
        </div>
    </div>
)}
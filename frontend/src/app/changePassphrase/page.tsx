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
    const [formValid, setFormValid] = React.useState(false);

    const handleChange = async () => {
        if (!passphrase.trim() || !newPassphrase.trim()) {
            alert("All Fields are required!");
            return;
        }
        try {
            const response = await instance.post("/changepassphrase", {prev_passphrase: passphrase, new_passphrase: newPassphrase});
            alert("Passphrase successfully changed!");
            router.push('/');
        } catch (error) {
            alert("Passphrase change failed. Please try again.");
        }
    };

    React.useEffect(() => {
        CheckFormValid();
    });

    function CheckFormValid() {
        if (passphrase !== "" && newPassphrase !== "" ) {
          setFormValid(true);
        } else {
          setFormValid(false);
        }
        return formValid
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
            <button className="button disabled:cursor-not-allowed" onClick={handleChange} disabled={formValid == false}>Change Passphrase</button>
        </div>
    </div>
)}
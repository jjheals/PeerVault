'use client'; //needed to handle site events (clicks / events / interactions)

import React from "react";
import Image from "next/image";
import { Model, User } from "@/model";
import { filesSelectController } from "@/controllers";
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { send } from "process";
import router from "next/router";

const PORT = 8000;

const instance = axios.create({
  baseURL:
    "http://localhost:" + PORT.toString(),
});

export default function AccountSettings() {

    const [model, setModel] = React.useState(new Model());
    const [redraw, forceRedraw] = React.useState(0);
    const [identity, setIdentity] = React.useState();
    const router = useRouter();

    function refresh() {
        forceRedraw(redraw + 1);
    }

    function retreiveIdentity(setIdentity) {
        let ret: User;
        instance
        .get("/ui/whoami")
        .then(function (response) {
            let data = response.data;
            console.log(data);
            ret = new User(data.pub_key, data.common_name, data.mac, data.ip);
            setIdentity(ret);
        })
        .catch (function (error) {
            console.log("errored:", error)
        });
    }

    React.useEffect(() => {
        if (!identity) {
            retreiveIdentity(setIdentity);
        }
      }, [redraw]);

    return (
        <div>
            <div className="header">
                <div className="header-row">
                    <div className="titleText">PeerVault</div>
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
                    <div className="icon-padding"></div>
                </div>
            </div>
            <hr className="h-px my-3 bg-gray-200 border-0 dark:bg-gray-700"></hr>
            <div className="subtitleText">Account Summary</div>
            <div className="grid grid-cols-[150px_1fr] gap-4 mt-2">
                <div className="font-semibold">Name: </div>
                <div>{identity?.common_name}</div>
                
                <div className="font-semibold">Public Key: </div>
                <div>{identity?.pub_key}</div>
                
                <div className="font-semibold">MAC Address: </div>
                <div>{identity?.mac}</div>
                
                <div className="font-semibold">IP Address: </div>
                <div>{identity?.ip}</div>
            </div>
            </div>
            
        </div>
    )



}
'use client'; //needed to handle site events (clicks / events / interactions)

import React, {Suspense} from "react";
import axios from "axios";
import { Model, User } from "@/model";
import { useRouter } from 'next/navigation';
import Image from "next/image";


const PORT = 8000;

const instance = axios.create({
  baseURL:
    "http://localhost:" + PORT.toString(),
});

export default function Home() {  
  const router = useRouter();
  const [redraw, forceRedraw] = React.useState(0);
  const [identity, setIdentity] = React.useState();
  const [localStorage, setLocalStorage] = React.useState(0.0);
  const [remoteStorage, setRemoteStorage] = React.useState(0.0);
  const [sharedStorage, setSharedStorage] = React.useState(0.0);
  // a list of json objects with a user name and the total amount of data stored in each of three categories
  const [userData, setUserData] = React.useState([]);
  
  function retreiveIdentity(setIdentity:any) {
      instance
      .get("/ui/whoami")
      .then(function (response) {
          let data = response.data;
          console.log(data);
          setIdentity(new User(data.pub_key, data.common_name, data.mac, data.ip));
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

  React.useEffect(() =>{
    instance
    .get("/ui/get-shared-by-peer")
    .then(function (response){
      setUserData(response.data["user_data"])
    })
    .catch (function (error) {
      console.error("errored:", error)
    });
  }, [redraw]);

  React.useEffect(() =>{
    instance
    .get("/ui/get-shared-storage")
    .then(function (response){
      setSharedStorage(response.data.storage);
    })
    .catch (function (error) {
      console.log("errored:", error)
    });
  }, [redraw]);

  React.useEffect(() =>{
    instance
    .get("/ui/get-remote-storage")
    .then(function (response){
      setRemoteStorage(response.data.storage);
    })
    .catch (function (error) {
      console.log("errored:", error)
    });
  }, [redraw]);

  React.useEffect(() =>{
    instance
    .get("/ui/get-local-storage")
    .then(function (response){
      setLocalStorage(response.data.storage);
    })
    .catch (function (error) {
      console.log("errored:", error)
    });
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
        <div className="break-all">{identity?.common_name}</div>

        <div className="font-semibold">Public Key: </div>
        <div className="break-all">{identity?.pub_key}</div>

        <div className="font-semibold">MAC Address: </div>
        <div className="break-all">{identity?.mac}</div>

        <div className="font-semibold">IP Address: </div>
        <div className="break-all">{identity?.ip}</div>

        <a className="button" href={'/changePassphrase'}>Change Passphrase</a>
      </div>

      <hr className="h-px my-3 bg-gray-200 border-0 dark:bg-gray-700"></hr>
      <div className="subtitleText">Quick Facts</div>
      <div className="grid grid-cols-[150px_1fr] gap-4 mt-2">
        <div className="font-semibold">Total Amount Stored Locally: </div>
        <div>{localStorage} Bytes</div>
        <div className="font-semibold">Total Amount Stored Remotely: </div>
        <div>{remoteStorage} Bytes</div>
        <div className="font-semibold">Total Amount Shared: </div>
        <div>{sharedStorage} Bytes</div>
        
      </div>
      <hr className="h-px my-3 bg-gray-200 border-0 dark:bg-gray-700"></hr>
      <div className="subtitleText">FAQ:</div>

      <div className="font-semibold">Can I change the account registered with this device? </div>
      <div>No </div>

      <div className="font-semibold">Can I change the amount of data allocated for storage locally? </div>
      <div>Yes...</div>

      <div className="font-semibold">Who made this site? </div>
      <div>Justin, Dan, Quentin and Lily!</div>

      <div>
    </div>
    </div>
  </div>)}
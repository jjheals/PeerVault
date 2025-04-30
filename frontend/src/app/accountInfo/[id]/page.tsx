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

  // a list of json objects with a user name and the total amount of data stored in each of three categories
  const [userData, setUserData] = React.useState({});
  
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
    if (!identity) return;

    instance
    .get("/ui/get-interacted-with-peers")
    .then(function (response){
      const userDataMap = response.data.user_data;
      const matchingKey = Object.keys(userDataMap).find((key) => {
        return key === identity.pub_key;
      });

      if (matchingKey) {
        setUserData(userDataMap[matchingKey]['storage_data']);
        console.log(userDataMap[matchingKey]['storage_data'])
      } else {
        console.warn("No matching key found for pub_key:", identity.pub_key);
      }
    })
    .catch (function (error) {
      console.error("errored:", error)
    });
  }, [redraw, identity]);

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
        <div className="font-semibold">Total Files Stored Locally: </div>
        <div>{userData['stored_locally'] ?? 0}</div>
        <div className="font-semibold">Total Files Stored Remotely: </div>
        <div>{userData['stored_remotely'] ?? 0}</div>
        <div className="font-semibold">Total Files Shared: </div>
        <div>{userData['shared'] ?? 0}</div>
        
      </div>
      <hr className="h-px my-3 bg-gray-200 border-0 dark:bg-gray-700"></hr>
      <div className="subtitleText">FAQ:</div>

      <div className="font-semibold">What is the purpose of this site? </div>
      <div>PeerVault provides a private, secure file transfer and storage system which does NOT leak sensistive information to any company. By keeping your data locally within a network, you can limit the amount of people with this data to the most strict possible circle.</div>

      <div className="font-semibold">Can I change the account registered with this device? </div>
      <div>No. It is crucial that the account is associated with the device so that data can always be located. There will only be one PeerVault account per device as it relies on your MAC Address. </div>

      <div className="font-semibold">What can I change about my accouht? </div>
      <div>You can change the amount of data you have allocated to store and the passphrase associated with this account. </div>

      <div className="font-semibold">Who made this site? </div>
      <div>Justin, Dan, Quentin and Lily!</div>

      <div>
    </div>
    </div>
  </div>)}
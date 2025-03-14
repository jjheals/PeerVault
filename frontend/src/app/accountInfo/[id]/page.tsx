'use client'; //needed to handle site events (clicks / events / interactions)

import React, {Suspense} from "react";
import axios from "axios";
import Table from "@/app/table"
import { TableSkeleton } from "@/app/skeletons";
import { useParams } from "next/navigation";
import { Model, User } from "@/model";
import { useRouter } from 'next/navigation';

const PORT = 8000;

const instance = axios.create({
  baseURL:
    "http://localhost:" + PORT.toString(),
});

export default function Home() {  
  const router = useRouter();
  const { id } = useParams(); // Get the dynamic `id` from the URL
  const [model, setModel] = React.useState(new Model());
  const [redraw, forceRedraw] = React.useState(0);
  // new User("","","","")
  const [identity, setIdentity] = React.useState();

  var user_list: any[] = [];
  var total_stored_remote_list: any[] = [];
  var total_stored_local_list: any[] = [];
  var total_shared_list: any[] = [];


  
  function refresh() {
      forceRedraw(redraw + 1);
  }
  
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
  
// TODO 
    // This needs to get the info from all-peers to connect pub_key with common_name
    // needs to get pub_key and connect that with the number of bytes for each type of file shown!!!
    // needs to be handled on the backend 

  const UserTable: React.FC = () => {
    return (
      <table className="w-full border-collapse border border-gray-300">
        <thead>
          <tr className="bg-gray-200">
            <th className="border p-2">Recipient</th>
            <th className="border p-2">Total Stored Remotely</th>
            <th className="border p-2">Total Stored Locally</th>
            <th className="border p-2">Total Shared</th>
            <th className="border p-2">View</th>
          </tr>
        </thead>
        <tbody>
          {user_list.map((user) => (
            <tr key={user.id} className="hover:bg-gray-100">
              <td className="border p-2">{user.id}</td>
              <td className="border p-2">{user.id}</td>
              <td className="border p-2">{user.id}</td>
              <td className="border p-2">{user.id}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

    return (
  <div>
    <div className="header">
      <div className="header-row">
        <div className="titleText">PeerVault</div>
        <div className="header-options-row">
          <div className="icon-padding"></div>
          <button onClick={()=> router.push("/")}>
            <div className="hover" title="Return Home">
              Home
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

      <hr className="h-px my-3 bg-gray-200 border-0 dark:bg-gray-700"></hr>
      <div className="subtitleText">Quick Facts</div>
      <div className="grid grid-cols-[150px_1fr] gap-4 mt-2">
        <div className="font-semibold">Total Amount Stored Locally: </div>
        <div>{0}</div>

        <div className="font-semibold">Total Amount Stored Remotely: </div>
        <div>{0}</div>

        <div className="font-semibold">Total Amount Shared: </div>
        <div>{0}</div>
      </div>
      <div>
        
      <hr className="h-px my-3 bg-gray-200 border-0 dark:bg-gray-700"></hr>
      <div className = "subtitleText">History Summary:</div>
      <div>
        <UserTable />
      </div>
    </div>
    </div>
  </div>)}
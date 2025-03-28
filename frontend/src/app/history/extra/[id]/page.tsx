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
  const { id } = useParams(); // Get the username from the URL
  const [redraw, forceRedraw] = React.useState(0);
  const [currentUser, setCurrentUser] = React.useState(""); // array of all users 
  const [peers, setPeers] = React.useState(""); // array peers


  const UserTable: React.FC = () => {
    
    return (
      <table className="w-full border-collapse border border-gray-300">
        <thead>
          <tr className="bg-gray-200">
          <th className="border p-2">Recipient</th>
            <th className="border p-2">Inbound/Outbound</th>
            <th className="border p-2">Filename</th>
            <th className="border p-2">Size</th>
            <th className="border p-2">Hash</th>
          </tr>
        </thead>

        {/* <tbody>
          {filteredUser && 
            flattenedhistory.map((file: any, index: number) => (
            file.length === 4? (
              <tr key={index} className="hover:bg-gray-100">
              <td className="border p-2">{currentUser}</td>
              <td className="border p-2">-</td>
              <td className="border p-2">{file[1]}</td>
              <td className="border p-2">{file[2]} Bytes</td>
              <td className="border p-2">{file[3]}</td>
            </tr>
            ) : file.length === 6? (
              <tr key={index} className="hover:bg-gray-100">
                <td className="border p-2">{currentUser}</td>
                <td className="border p-2">{file[1]}</td>
                <td className="border p-2">{file[2]}</td>
                <td className="border p-2">{file[3]} Bytes</td>
                <td className="border p-2">{file[4]}</td>
              </tr>
            ) : (
              <tr key={index} className="hover:bg-gray-100">
                <td className="border p-2" colSpan={5}>
                  Invalid file format: {file}
                </td>
              </tr>
            )
          ))
          }
        </tbody> */}
      </table>
    );
  };

  // Get the identity of the User on this device...
  React.useEffect(() =>{
    instance
    .get("/ui/whoami")
    .then(function (response){
      if(response.data["common_name"] != undefined){
        setCurrentUser(response.data["common_name"]);
      }

    })
    .catch (function (error) {
      console.error("errored:", error)
    });
  }, [redraw]);

  // Get the identity of the User on this device...
  React.useEffect(() =>{
    instance
    .get("/ui/get-peer-list")
    .then(function (response){
      setPeers(response.data)
    })
    .catch (function (error) {
      console.error("errored:", error)
    });
  }, [redraw]);

  return (
    <div>
        <div className="header">
          <div className="header-row">
            <div className="titleText">User: {currentUser}</div>
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

          <div>
            <UserTable />
          </div>
        </div>
      </div>
  )}
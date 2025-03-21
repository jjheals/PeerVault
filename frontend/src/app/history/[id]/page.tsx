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
  const username_url = decodeURIComponent(id);
  const [redraw, forceRedraw] = React.useState(0);
  const [userList, setUserList] = React.useState<any[]>([]);  // array of all users 
  const [currentUser, setCurrentUser] = React.useState(username_url as string);  // array of all users 

  const UserTable: React.FC = () => {
    // Filter history for the selected user
    const filteredUser = userList.find(entry => entry.user === currentUser);
    
    if(!filteredUser){
      return (
        <div className="text-red-500">No history found for user: {currentUser}</div>
      );
    }

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
        <tbody>
          {filteredUser && 
            filteredUser.history.map((file: any, index: number) => (
            file.length === 4? (
              <tr key={index} className="hover:bg-gray-100">
              <td className="border p-2">{file[0]}</td>
              <td className="border p-2">-</td>
              <td className="border p-2">{file[1]}</td>
              <td className="border p-2">{file[2]} Bytes</td>
              <td className="border p-2">{file[3]}</td>
            </tr>
            ) : file.length === 5?(
              <tr key={index} className="hover:bg-gray-100">
                <td className="border p-2">{file[0]}</td>
                <td className="border p-2">{file[1]}</td>
                <td className="border p-2">{file[2]}</td>
                <td className="border p-2">{file[3]} Bytes</td>
                <td className="border p-2">{file[4]}</td>
              </tr>
            ) : (
              <tr key={index} className="hover:bg-gray-100">
                <td className="border p-2" colSpan={5}>
                  Invalid file format
                </td>
              </tr>
            )
          ))
          }
        </tbody>
      </table>
    );
  };

  console.log(currentUser)

  React.useEffect(() =>{
    instance
    .get("/ui/get-user-history")
    .then(function (response){

    })
    .catch (function (error) {
      console.error("errored:", error)
    });
  }, [redraw]);

  React.useEffect(() =>{
    instance
    .get("/ui/get-user-history")
    .then(function (response){
      var list = response.data["all_user_data"];
      setUserList(list)
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
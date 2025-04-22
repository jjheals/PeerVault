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
  const params = useParams();
  console.log(params);
  const current_user = decodeURIComponent(params.current);
  const other_user = decodeURIComponent(params.other);
  const [otherPubKey, setOtherPubKey] = React.useState(null);
  const [redraw, forceRedraw] = React.useState(0);
  const [history, setHistory] = React.useState(null);  // user data
  // const [currentUser, setCurrentUser] = React.useState(username_url as string);
  // const [otherUser, setOther] = React.useState(username_url as string);

 function retreiveHistory() {

    instance
    .post("/ui/get-user-history-specific", {
      other_user: other_user
    })
    .then(function (response) {
      setHistory(response.data.user_data);
    })
    .catch(function (error) {
      console.log(error);
    });
  }

  React.useEffect(() =>{
    if (!history) {
      retreiveHistory()
    }
  }, [history, current_user]);

  function retreiveOtherPubKey() {

    instance
    .post("/ui/get-pub-key", {
      peer_common_name: other_user
    })
    .then(function (response) {
      setOtherPubKey(response.data.peer_pub_key);
    })
    .catch(function (error) {
      console.log(error);
    });
  }

  React.useEffect(() =>{
    if (!history) {
      retreiveOtherPubKey()
    }
  }, [history, current_user, other_user]);

  const UserTable: React.FC = () => {
    
  if (!history || !Array.isArray(history)) {
    return <div className="text-red-500">Loading history ...</div>;
  }


  return (
      <table className="w-full border-collapse border border-gray-300">
        <thead>
          <tr className="bg-gray-200">
            <th className="border p-2">Filename</th>
            <th className="border p-2">Size</th>
            <th className="border p-2">Inbound/Outbound</th>
            <th className="border p-2">Hash</th>
          </tr>
        </thead>
        <tbody>
          {history.map((file: any, index: number) => (
            file.peer_pub_key && file.filename && file.sha256 && file.size_gb ? (
              <tr key={index} className="hover:bg-gray-100">
                <td className="border p-2">{file.filename}</td>
                <td className="border p-2">{file.size_gb} GB</td>
                <td className="border p-2">{file.direction == null ? '-' : file.direction}</td>
                <td className="border p-2">{file.sha256}</td>
              </tr>
            ) : (
              <tr key={index} className="hover:bg-gray-100">
                <td className="border p-2" colSpan={5}>
                  Invalid file format
                </td>
              </tr>
            )
          ))}
        </tbody>
      </table>
    );
  };

  console.log(current_user)

  return (
    <div>
        <div className="header">
          <div className="header-row">
            <div className="titleText">User: {current_user}</div>
            <div className="header-options-row">
              <a href={`/accountInfo/${current_user}`} className="hover" title="Account Settings">
                  <Image
                    className="dark"
                    src="/settings-2-svgrepo-com.svg"
                    alt="account settings icon"
                    width={50}
                    height={50}
                  />
              </a>
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
            <div className="subtitleText">Recipient: {other_user}</div>
            <div className="subtitleText">Recipient Public Key: {otherPubKey}</div>
            <UserTable />
          </div>
        </div>
      </div>
  )}
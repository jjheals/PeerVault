'use client'; //needed to handle site events (clicks / events / interactions)

import React from "react";
import Image from "next/image";
import { Model } from "@/model";
import { filesSelectController } from "@/controllers";
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { motion } from "framer-motion";

const PORT = 8000;

const instance = axios.create({
  baseURL:
    "http://localhost:" + PORT.toString(),
});


export default function Home() {
    const [model, setModel] = React.useState(new Model());
    const [redraw, forceRedraw] = React.useState(0);
    const [files, setFiles] = React.useState<any[]>([]);
    const [recipient, setRecipient] = React.useState("");
    const [users, setUsers] = React.useState<any[]>([]);
    const [identity, setIdentity] = React.useState({});
    const [verifiedUser, setVerifiedUser] = React.useState(false)
    const [sendType, setSendType] = React.useState("");
    const [formValid, setFormValid] = React.useState(false);

    // for the sharing flow...
    const [showStartSharing, setShowStartSharing] = React.useState(true);
    const [showSelectRecipient, setShowSelectRecipient] = React.useState(false);
    const [showFileSelect, setShowFileSelect] = React.useState(false);
    const [showStorageType, setShowStorageType] = React.useState(false);
    const [showConfirmation, setShowConfirmation] = React.useState(false);

    // for the icons
    const [numSendReq, setNumSendReq] = React.useState(0);
    const [numIncomingReq, setNumIncomingReq] = React.useState(0);
    
    // for the history table...
    const [userData, setUserData] = React.useState([]);


    const router = useRouter();

    function refresh() {
        forceRedraw(redraw + 1);
    }

    React.useEffect(() =>{
      instance
      .get("/ui/get-peer-list")
      .then(function (response){
        var userlist = []
        for (let i = 0; i < response.data.length; i++) {
          userlist.push(response.data[i].common_name);
        }
        setUsers(userlist);
      })
      .catch (function (error) {

        console.error("errored:", error)
      });
    }, [redraw]);

    // Get the identity of the User on this device...
    React.useEffect(() =>{
      instance
      .get("/ui/whoami")
      .then(function (response){

        if(response.data["common_name"] != ""){
          response.data.pub_key = response.data.pub_key
          setIdentity(response.data);
          console.log(response.data)
          setVerifiedUser(true);
        }else{
          setVerifiedUser(false)
        }

      })
      .catch (function (error) {
        console.error("errored:", error)
      });
    }, [redraw]);

    React.useEffect(() =>{
      instance
      .get("/ui/get-pending-requests")
      .then(function (response){
        const outgoing = response.data["outgoing_requests"] || [];
        const incoming = response.data["incoming_requests"] || [];
        setNumSendReq(outgoing.length);
        setNumIncomingReq(incoming.length);
      })
      .catch (function (error) {
        console.error("errored:", error)
      });
    }, [redraw]);


    // store the uploaded files
    React.useEffect(() => {
      retreiveFilesToUpload(setFiles);
    }, [redraw]);


    // check if th upload functionality should be enabled
    React.useEffect(() => {
        CheckFormValid();
    }, [recipient, sendType, files]);


    // allow the user to REMOVE a file that has been selected from the list
    const removeFile = (fileToRemove: number) =>{
      model.removeFile(fileToRemove);
      refresh()
    }


    // display the list of files selected to be shared or sent
    function FilesList(props: any) {
      if(!props.files) return;

      return (
        <div>
          <label>Total Size of Files: {model.getTotalStorage().toString()}B</label>
          {props.files.map((file: any, index: any) => (
            <p key={index}>
              <label>{file.name} - {file.size}B </label>
              <button className= "redButton" onClick={() =>removeFile(index)} >X</button>
            </p>
          ))}
        </div>
      )
    }

    // display the list of files selected to be shared or sent
    function FileConfirmationList(props: any) {
      if(!props.files) return;

      return (
        <div>
          <label>Total Size of Files: {model.getTotalStorage().toString()}B</label>
          {props.files.map((file: any, index: any) => (
            <p key={index}>
              <label>{file.name} - {file.size}B </label>
            </p>
          ))}
        </div>
      )
    }


    // stores the value for the files that have been selected
    function handleFilesSelect(event: any) {
      filesSelectController(model, event.target.files, refresh);
      event.target.value = ""
    }

    // get files & info from device 
    function retreiveFilesToUpload(setFiles: any) {
      setFiles(model.getFilesToUpload());
    }

    // stores the value for the recipient of the share
    const selectRecipient = (event: React.ChangeEvent<HTMLSelectElement>) => {
      setRecipient(event.target.value);
    };

    // display the users that we are available to share/store with
    function DisplayUsers(props: any) {      
      if (!props.users) return <div>Loading</div>;

      return (
        <select id="users" value={recipient} onChange={selectRecipient}>
          <option value="" disabled>Select an option</option>

          {props.users.map((users: any, index: any) => (
            <option key={index} value={users}>{users}</option>
          ))}
        </select>
      )
    }

    // stores the value for the type of file upload (share/store)
    const selectSendType = (event: React.ChangeEvent<HTMLSelectElement>) => {
      setSendType(event.target.value);
    };

    // checks if there is data selected for recipient, files selected AND a send type
    function CheckFormValid() {
      if (sendType !== "" && recipient !== "" && files.length > 0) {
        setFormValid(true);
      } else {
        setFormValid(false);
      }
    };

    React.useEffect(() =>{
      instance
      .get("/ui/get-interacted-with-peers")
      .then(function (response){
        const userDataArray = Object.entries(response.data["user_data"]).map(([key, value]) => ({
          publicKey: key,
          ...value, // Spread the rest of the data
        }));
        console.log(userDataArray)
        setUserData(userDataArray)
      })
      .catch (function (error) {
        console.error("errored:", error)
      });
    }, [redraw]);

    function uploadData() {  
      const formData = new FormData();

      model.filesToUpload.forEach((fileObj: any, index: number) => {
        formData.append(`files`, fileObj.file);
      });
      formData.append("peer_pub_key", recipient);
      formData.append("send_method", sendType);

      instance
      .post("/ui/upload-data", formData, {headers: {"Content-Type": "multipart/form-data",},})
      .then(()=>{
        alert("Uploaded Data!")
      })
      .catch (function (error) {
        alert("failed:" + error)
      });

      //remove all of the data??
      setRecipient("")
      setFiles([])
      model.filesToUpload = []
      setSendType("")
    }

    const handleContinue = (value:number) => {
      if (value == 1) {
        setShowStartSharing(false);
        setShowSelectRecipient(true);
      }
      else if (value == 2) {
        setShowSelectRecipient(false);
        setShowFileSelect(true);
      }
      else if (value == 3) {
        setShowFileSelect(false);
        setShowStorageType(true);
      }
      else if (value == 4) {
        setShowStorageType(false);
        setShowConfirmation(true);
      }
      else if (value == 5) {
        uploadData();
        returnHome();
      }
      refresh();
    };

    function resetShow() {
      setShowSelectRecipient(false);
      setShowFileSelect(false);
      setShowStorageType(false);
      setShowConfirmation(false);
    }

    function handleCancel(event:any) {
      setShowStartSharing(true);
      resetShow();
      setRecipient("")
      setFiles([])
      model.filesToUpload = []
      setSendType("")
      refresh();
    }

    function returnHome() {
      setShowStartSharing(true);
      resetShow();
      refresh();
    }

    const UserTable: React.FC = () => {
        return (
          <div>
            <div className="titleText"> File History </div>
            <table className="w-full border-collapse border border-gray-300">

            <thead>
              <tr className="bg-gray-200">
                <th className="border p-2">Recipient</th>
                <th className="border p-2">Total Files Stored Remotely</th>
                <th className="border p-2">Total Files Stored Locally</th>
                <th className="border p-2">Total Files Shared</th>
                <th className="border p-2">View</th>
              </tr>
            </thead>
            <tbody>
              {userData
                .filter(user => user.publicKey !== identity.pub_key)
                .map((user) => (
                <tr key={user.publicKey} className="hover:bg-gray-100">
                  <td className="border p-2 text-center">{user.common_name}</td>
                  <td className="border p-2 text-center">{user.storage_data.stored_remotely}</td>
                  <td className="border p-2 text-center">{user.storage_data.stored_locally}</td>
                  <td className="border p-2 text-center">{user.storage_data.shared}</td>
                  <td className="border p-2 text-center"> 
                    <a href={`/history/${identity.common_name}/${user.common_name}`} className="hover" title="Detailed View">
                        <Image
                          className="mx-auto dark"
                          src="/info-circle-svgrepo-com.svg"
                          alt="History"
                          width={30}
                          height={30}
                        />
                    </a>  
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          
        );
      };


    return (
      <div>
      <div className="header">
        <div className="header-row">
          <div className="titleText">PeerVault</div>

          {!verifiedUser && (            
            <div className="header-options-row">            
              <button onClick={()=> router.push("/createAccount/")}>
                <div className="button">Create Account</div>
              </button>
            </div>
          )}
          {verifiedUser && (
            <div className="header-options-row">
              <div className="relative inline-block">
                <button onClick={() => router.push("/pendingRequests/sent")}>
                  <div className="hover" title="Pending Sent Requests">
                    <Image
                      className="dark"
                      src="/send-svgrepo-com.svg"
                      alt="pending sent icon"
                      width={50}
                      height={50}
                    />
                  </div>
                </button>
                {numSendReq > 0 ? (
                  <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-white text-xs font-bold">
                  {numSendReq}
                </span>
                ): null}
                
              </div>
              <div className="icon-padding"></div>
              <div className="relative inline-block">
                <button onClick={() => router.push("/pendingRequests/incoming")}>
                  <div className="hover" title="Incoming Requests">
                    <Image
                      className="dark"
                      src="/inbox-alt-1-svgrepo-com.svg"
                      alt="incoming request icon"
                      width={50}
                      height={50}
                    />
                  </div>
                </button>
                {numIncomingReq  > 0 ? (
                <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-white text-xs font-bold">
                  {numIncomingReq}
                </span>
                ): null}
              </div>
              <div className="icon-padding"></div>
              <a href={`/accountInfo/${identity.common_name}`} className="hover" title="Account Settings">
                  <Image
                    className="dark"
                    src="/settings-2-svgrepo-com.svg"
                    alt="account settings icon"
                    width={50}
                    height={50}
                  />
              </a>
              <div className="icon-padding"></div>
            </div>
          )}
        </div>
        
        {verifiedUser && (
            <div className = "subtitleText">              
                Welcome, {identity.common_name}
            </div>
          )}

      <hr className="h-px my-3 bg-gray-200 border-0 dark:bg-gray-700"></hr>
      </div>
        {verifiedUser && showStartSharing && (
          <div>
            <div className="flex items-center justify-center">
              <motion.button
                className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg"
                animate={{ opacity: [1, 0.5, 1] }}
                transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                onClick={() => handleContinue(1)}
              >
                Start Sharing
              </motion.button>
            </div>
          </div>
        )}

        {verifiedUser && showSelectRecipient && (
          <div>
            <div className="ItemContainer">
              <div className="itemContainerContent">
                <div className="itemCard">
                  <div className="itemCardTitleText">Select a Person to Share With</div>
                  <div>
                    <div className="dropdown">
                      <button className="dropbtn">Possible Recipients</button>
                      <div className="dropdown-content">
                      <div>
                        <label htmlFor="users">Choose a user: </label>
                        <DisplayUsers users={users}/>
                      </div>
                      </div>
                    </div>
                  </div>
                  <div>
                    {recipient && <p>You selected: {recipient}</p>}
                  </div>
                </div>
              </div>
            </div>
            <div className="flex items-center justify-center flex-col space-y-4">
              <div>
                <button className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg disabled:bg-gray-400 disabled:cursor-not-allowed" onClick={() => handleContinue(2)} disabled={recipient === ""}>
                  Continue
                </button>
              </div>
              <div>
                <button className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg" onClick={handleCancel}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
        {verifiedUser && showFileSelect && (
          <div>
            <div className="ItemContainer">
              <div className="itemContainerContent">
                <div className="itemCard">
                  <div className="itemCardTitleText">Select Files to Share</div>
                  <p>
                    
                  <input
                    type="file"
                    id="fileInput"
                    onChange={handleFilesSelect}
                    className="hidden"
                    multiple
                  />

                  {/* Custom Upload Button */}
                  <label 
                    htmlFor="fileInput" 
                    className="bg-blue-500 text-white px-4 py-2 rounded cursor-pointer"
                  >
                    Select Files
                  </label>
                  </p>
                  <div>
                    <FilesList files={files}/>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex items-center justify-center flex-col space-y-4">
              <div>
                <button className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg disabled:bg-gray-400 disabled:cursor-not-allowed" onClick={() => handleContinue(3)} disabled={files.length == 0}>
                  Continue
                </button>
              </div>
              <div>
                <button className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg" onClick={handleCancel}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
        {verifiedUser && showStorageType && (
          <div>
            <div className="ItemContainer">
              <div className="itemContainerContent">
                <div className="itemCard">
                  <div className="itemCardTitleText">Storage Type</div>
                    <select id="sendType" value={sendType} onChange={selectSendType}>
                      <option value="" disabled>Select an type</option>
                      <option value="Share">Share</option>
                      <option value="Store">Store</option>
                    </select>
                    
                    {sendType && <p>You selected: {sendType}</p>}
                </div> 
              </div>
            </div>
            <div className="flex items-center justify-center flex-col space-y-4">
              <div>
                <button className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg disabled:bg-gray-400 disabled:cursor-not-allowed" onClick={() => handleContinue(4)} disabled={sendType === ""}>
                  Continue
                </button>
              </div>
              <div>
                <button className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg" onClick={handleCancel}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
        {verifiedUser && showConfirmation && (
          <div>
            <div className="ItemContainer">
              <div className="itemContainerContent">
                <div className="itemCard">
                  <div className="itemCardLeftContent">
                    <div className="itemCardTitleText">Confirmation</div>
                      <div>Storage Type: {sendType}</div>
                      <div>
                        <FileConfirmationList files={files}/>
                      </div>
                  </div>
                </div> 
              </div>
            </div>
            <div className="flex items-center justify-center flex-col space-y-4">
              <div>
                <button className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg" onClick={() => handleContinue(5)}>
                  Upload
                </button>
              </div>
              <div>
                <button className="px-6 py-3 text-xl font-bold text-white bg-blue-500 rounded-lg shadow-lg" onClick={handleCancel}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        { !verifiedUser || (showSelectRecipient || showFileSelect || showStorageType || showConfirmation) ? (
          null
        ):         
        <div>
          <UserTable />
        </div>}

      </div>
    )
  }
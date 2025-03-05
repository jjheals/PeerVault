'use client'; //needed to handle site events (clicks / events / interactions)

import React from "react";
import { Model } from "@/model";
import { filesSelectController } from "@/controllers";
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { send } from "process";

const PORT = 4303;

const instance = axios.create({
  baseURL:
    "http://localhost:" + PORT.toString(),
});

export default function Home() {
    const [model, setModel] = React.useState(new Model())
    const [redraw, forceRedraw] = React.useState(0);
    const [files, setFiles] = React.useState([]);
    const [recipient, setRecipient] = React.useState("");
    const [users, setUsers] = React.useState(undefined);
    const [identity, setIdentity] = React.useState();
    const [verfifiedUser, setVerifiedUser] = React.useState(false)
    const [sendType, setSendType] = React.useState("");
    const [formValid, setFormValid] = React.useState(false);



    function refresh() {
        forceRedraw(redraw + 1);
    }

    React.useEffect(() =>{
      instance
      .get("/users")
      .then(function (response){
        // The response is the response of the get request
        console.log("ret: ", response.data.users);
        setUsers(response.data.users);
      })
      .catch (function (error) {
        console.log("errored:", error)
      });
    }, [redraw]);



    React.useEffect(() =>{
      instance
      .get("/whoAmI")
      .then(function (response){
        console.log("me: ", response.data.identity);
        setIdentity(response.data.identity);
        if (response.data.identity != "Guest") {
          setVerifiedUser(true);
        }
      })
      .catch (function (error) {
        console.log("errored:", error)
      });
    }, [redraw]);


    React.useEffect(() => {
      retreiveFilesToUpload(setFiles);
      console.log("files:", files);
    }, [redraw]);

    React.useEffect(() => {
        CheckFormValid();
    }, [recipient, sendType, files]);

    function FilesList(props: any) {
      if(!props.files) return;

      return (
        <div>
          <label>Total Size of Files: {model.getTotalStorage().toString()}</label>
          {props.files.map((file: any, index: any) => (
            <p key={index}>
              <label>{file.name} - {file.size}B</label>
            </p>
          ))}
        </div>
      )
    }

    function handleFilesSelect(event: any) {
      filesSelectController(model, event.target.files, refresh);
    }

    function retreiveFilesToUpload(setFiles: any) {
      setFiles(model.getFilesToUpload());
    }

    const selectRecipient = (event: React.ChangeEvent<HTMLSelectElement>) => {
      setRecipient(event.target.value);
      console.log(recipient);
    };
    const router = useRouter();

    function DisplayUsers(props: any) {      
      if (!props.users) return <div>Loading</div>;
      console.log("props:", props.users);
      return (
        <select id="users" value={recipient} onChange={selectRecipient}>
          <option value="" disabled>Select an option</option>

          {props.users.map((users: any, index: any) => (
            <option key={index} value={users}>{users}</option>
          ))}
        </select>
      )
    }

    const selectSendType = (event: React.ChangeEvent<HTMLSelectElement>) => {
      setSendType(event.target.value);
    };

    function CheckFormValid() {
      if (sendType !== "" && recipient !== "" && files.length > 0) {
        setFormValid(true);
      } else {
        setFormValid(false);
      }
    };

    function uploadData() {  
      var toUser = recipient; 
      var files:any = files;
      var sendMethod = sendType;
         
      console.log("called upload");

      instance
      .post("/uploadData",
        {
          recipient: toUser,
          data: files,
          sendMethod: sendMethod
        }
      )
      .then(function (response){
        console.log("success");
      })
      .catch (function (error) {
        console.log("errored")
      });

      //remove all of the data??
      setRecipient("")
      setFiles([])
      setSendType("")
    }

    return (
      <div>
      <div className="header">
        <div className="header-row">
          <div className="titleText">PeerVault</div>
          <div className="subtitleText">Welcome, {identity}!</div>
          {!verfifiedUser && (
            <div className="header-options-row">
              <button onClick={()=> router.push("/createAccount/")}>
                <div className="header-button-text-option-two">Create Account</div>
              </button>
            </div>
          )}
          
        </div>
      </div>
        {verfifiedUser && (
          <div>
          <hr className="h-px my-3 bg-gray-200 border-0 dark:bg-gray-700"></hr>
          
            <div className="ItemContainer">
              <div className="itemContainerContent">
                <div className="itemCard">

                  <div className="itemCardLeftContent">
                    <div className="itemCardTitleText">Select a Person to Share With</div>
                    <div className="dropdown">
                      <button className="dropbtn">Possible Recipients</button>
                      <div className="dropdown-content">
                      <div>
                        <label htmlFor="users">Choose a user: </label>
                        <DisplayUsers users={users}/>
                      </div>
                      </div>
                    </div>
                    {recipient && <p>You selected: {recipient}</p>}
                  </div> 
                </div>


                <div className="itemCard">
                  <div className="itemCardLeftContent">
                    <div className="itemCardTitleText">Select Files to Share</div>
                    <p>
                      <input type="file" multiple onChange={handleFilesSelect}/>
                    </p>
                    <div>
                      <FilesList files={files}/>
                    </div>
                  </div> 
                </div>


                <div className="itemCard">
                  <div className="itemCardLeftContent">
                    <div className="itemCardTitleText">Storage Type</div>
                      <select id="sendType" value={sendType} onChange={selectSendType}>
                        <option value="" disabled>Select an type</option>
                        <option value="share">Share</option>
                        <option value="store">Store</option>
                      </select>
                      
                      {sendType && <p>You selected: {sendType}</p>}
                  </div>
                </div> 

                <div className="itemCard">
                  <button className="button" onClick={()=> uploadData()} disabled={!formValid}>Upload</button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    )

}